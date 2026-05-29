from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..database import get_db

router = APIRouter()


def require_admin(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/")
async def list_users(request: Request, db=Depends(get_db)):
    require_admin(request)
    rows = db.execute(
        "SELECT id, name, is_admin, is_editor, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


class RoleUpdate(BaseModel):
    is_editor: bool | None = None
    is_admin:  bool | None = None


@router.patch("/{orcid_uri:path}")
async def update_user_roles(
    orcid_uri: str,
    data: RoleUpdate,
    request: Request,
    db=Depends(get_db),
):
    require_admin(request)
    row = db.execute("SELECT id FROM users WHERE id = ?", (orcid_uri,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    if data.is_editor is not None:
        db.execute("UPDATE users SET is_editor = ? WHERE id = ?", (int(data.is_editor), orcid_uri))
    if data.is_admin is not None:
        db.execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(data.is_admin), orcid_uri))
    db.commit()

    updated = db.execute(
        "SELECT id, name, is_admin, is_editor FROM users WHERE id = ?", (orcid_uri,)
    ).fetchone()
    return dict(updated)
