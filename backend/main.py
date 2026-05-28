import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import get_db, init_db
from .routes import annotations, auth, exports, manifests, volumes

load_dotenv()

app = FastAPI(
    title="Toganoo Collection Provenance Annotation Tool",
    description="IIIF annotation pipeline for provenance data curation",
    version="0.2.0",
)

_BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
    max_age=86400 * 7,
    https_only=os.getenv("HTTPS_ONLY", "false").lower() == "true",
    same_site="lax",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_BASE_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
async def startup():
    init_db()


# API routes
app.include_router(auth.router,        prefix="/auth",              tags=["auth"])
app.include_router(annotations.router, prefix="/api/annotations",   tags=["annotations"])
app.include_router(volumes.router,     prefix="/api/volumes",       tags=["volumes"])
app.include_router(manifests.router,   prefix="/api/manifest",      tags=["manifests"])
app.include_router(exports.router,     prefix="/api/export",        tags=["exports"])


@app.get("/api/health")
async def health():
    try:
        db_gen = get_db()
        db = next(db_gen)
        db.execute("SELECT 1")
        try:
            next(db_gen)
        except StopIteration:
            pass
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


_DIST_DIR = "frontend/dist"

# Serve hashed JS/CSS/image assets
app.mount("/assets", StaticFiles(directory=f"{_DIST_DIR}/assets"), name="assets")


# SPA catch-all — returns index.html for any path not matched above,
# or a static file if one exists at that path (e.g. favicon.ico)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    candidate = os.path.join(_DIST_DIR, full_path)
    if full_path and os.path.isfile(candidate):
        return FileResponse(candidate)
    return FileResponse(os.path.join(_DIST_DIR, "index.html"))
