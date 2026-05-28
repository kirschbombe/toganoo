import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth

from ..database import get_db

router = APIRouter()

# ── Dev mode ──────────────────────────────────────────────────────────────────
# Set ORCID_CLIENT_ID=dev in .env to bypass OAuth entirely.
# A mock user is injected automatically — no credentials needed.
DEV_MODE = os.getenv("ORCID_CLIENT_ID", "").strip().lower() == "dev"

# Comma-separated ORCID URIs of users who should have is_admin=1
_ADMIN_ORCIDS = {
    o.strip() for o in os.getenv("ADMIN_ORCIDS", "").split(",") if o.strip()
}

DEV_USER = {
    "orcid": "https://orcid.org/0000-0000-0000-0000",
    "name":  "Dev User (local)",
    "is_admin": True,
}

# ── OAuth (production / sandbox) ─────────────────────────────────────────────
ORCID_BASE = (
    "https://sandbox.orcid.org"
    if os.getenv("ORCID_SANDBOX", "true").lower() == "true"
    else "https://orcid.org"
)

oauth = OAuth()
if not DEV_MODE:
    oauth.register(
        name="orcid",
        client_id=os.getenv("ORCID_CLIENT_ID"),
        client_secret=os.getenv("ORCID_CLIENT_SECRET"),
        server_metadata_url=f"{ORCID_BASE}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid"},
    )


def _upsert_user(db, orcid_uri: str, name: str):
    is_admin = 1 if orcid_uri in _ADMIN_ORCIDS else 0
    db.execute(
        """INSERT INTO users (id, name, is_admin)
           VALUES (?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               name = excluded.name,
               is_admin = MAX(is_admin, excluded.is_admin)""",
        (orcid_uri, name, is_admin),
    )
    db.commit()
    row = db.execute("SELECT is_admin FROM users WHERE id = ?", (orcid_uri,)).fetchone()
    return bool(row["is_admin"]) if row else bool(is_admin)


@router.get("/login")
async def login(request: Request):
    if DEV_MODE:
        db_gen = get_db()
        db = next(db_gen)
        try:
            _upsert_user(db, DEV_USER["orcid"], DEV_USER["name"])
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
        request.session["user"] = DEV_USER
        return RedirectResponse("/")
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
    redirect_uri = f"{base_url}/auth/callback"
    return await oauth.orcid.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    if DEV_MODE:
        request.session["user"] = DEV_USER
        return RedirectResponse("/")

    try:
        token = await oauth.orcid.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/?error=auth_failed")

    userinfo = token.get("userinfo", {})
    orcid_id = userinfo.get("sub", "").replace("-", "")
    if not orcid_id:
        return RedirectResponse("/?error=auth_failed")
    orcid_uri = f"https://orcid.org/{orcid_id[:4]}-{orcid_id[4:8]}-{orcid_id[8:12]}-{orcid_id[12:]}"

    name = userinfo.get("name") or (
        userinfo.get("given_name", "") + " " + userinfo.get("family_name", "")
    )
    name = name.strip() or orcid_uri

    db_gen = get_db()
    db = next(db_gen)
    try:
        is_admin = _upsert_user(db, orcid_uri, name)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    request.session["user"] = {"orcid": orcid_uri, "name": name, "is_admin": is_admin}
    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/me")
async def me(request: Request):
    user = request.session.get("user")
    return JSONResponse({"user": user})  # includes is_admin if present
