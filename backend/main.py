import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .database import init_db
from .routes import annotations, auth, exports, manifests

load_dotenv()

app = FastAPI(
    title="Toganoo Collection Provenance Annotation Tool",
    description="IIIF annotation pipeline for provenance data curation",
    version="0.1.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
    max_age=86400 * 7,
    https_only=os.getenv("HTTPS_ONLY", "false").lower() == "true",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


# API routes
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(annotations.router, prefix="/api/annotations", tags=["annotations"])
app.include_router(manifests.router, prefix="/api/manifest", tags=["manifests"])
app.include_router(exports.router, prefix="/api/export", tags=["exports"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend — must be last so API routes take priority
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
