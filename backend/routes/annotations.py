import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..database import get_db

router = APIRouter()


class AnnotationCreate(BaseModel):
    volume_id: str
    canvas_id: str
    canvas_label: Optional[str] = None
    region_xywh: str
    mark_type: str
    shape: Optional[str] = None
    ink_color: Optional[str] = None
    script_type: Optional[str] = None
    condition: Optional[str] = None
    transcription: Optional[str] = None
    transcription_rom: Optional[str] = None
    owner_name: Optional[str] = None
    owner_type: Optional[str] = None
    owner_authority_uri: Optional[str] = None
    place_name: Optional[str] = None
    place_authority_uri: Optional[str] = None
    location_on_object: Optional[str] = None
    notes: Optional[str] = None


def require_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@router.get("/volume/{volume_id:path}")
async def get_volume_annotations(volume_id: str, db=Depends(get_db)):
    """Return all annotations for a given volume_id (manifest URL or ARK)."""
    rows = db.execute(
        "SELECT * FROM annotations WHERE volume_id = ? ORDER BY created_at",
        (volume_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/")
async def create_annotation(
    request: Request,
    data: AnnotationCreate,
    db=Depends(get_db),
):
    user = require_user(request)
    now = datetime.now(timezone.utc).isoformat()
    anno_id = str(uuid.uuid4())

    db.execute(
        """INSERT INTO annotations (
               id, volume_id, canvas_id, canvas_label, region_xywh,
               mark_type, shape, ink_color, script_type, condition,
               transcription, transcription_rom,
               owner_name, owner_type, owner_authority_uri,
               place_name, place_authority_uri,
               location_on_object, notes,
               annotator_orcid, annotator_name, created_at, updated_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            anno_id, data.volume_id, data.canvas_id, data.canvas_label, data.region_xywh,
            data.mark_type, data.shape, data.ink_color, data.script_type, data.condition,
            data.transcription, data.transcription_rom,
            data.owner_name, data.owner_type, data.owner_authority_uri,
            data.place_name, data.place_authority_uri,
            data.location_on_object, data.notes,
            user["orcid"], user["name"], now, now,
        ),
    )
    db.commit()
    return {"id": anno_id, "created_at": now}


@router.put("/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    request: Request,
    data: AnnotationCreate,
    db=Depends(get_db),
):
    user = require_user(request)
    row = db.execute(
        "SELECT annotator_orcid FROM annotations WHERE id = ?", (annotation_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if row["annotator_orcid"] != user["orcid"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this annotation")

    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """UPDATE annotations SET
               mark_type=?, shape=?, ink_color=?, script_type=?, condition=?,
               transcription=?, transcription_rom=?,
               owner_name=?, owner_type=?, owner_authority_uri=?,
               place_name=?, place_authority_uri=?,
               location_on_object=?, notes=?, updated_at=?
           WHERE id=?""",
        (
            data.mark_type, data.shape, data.ink_color, data.script_type, data.condition,
            data.transcription, data.transcription_rom,
            data.owner_name, data.owner_type, data.owner_authority_uri,
            data.place_name, data.place_authority_uri,
            data.location_on_object, data.notes, now,
            annotation_id,
        ),
    )
    db.commit()
    return {"id": annotation_id, "updated_at": now}


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str, request: Request, db=Depends(get_db)
):
    user = require_user(request)
    row = db.execute(
        "SELECT annotator_orcid FROM annotations WHERE id = ?", (annotation_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if row["annotator_orcid"] != user["orcid"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    db.commit()
    return {"deleted": annotation_id}
