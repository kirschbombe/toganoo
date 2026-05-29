from urllib.parse import urlparse

import httpx
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..database import get_db

router = APIRouter()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def require_admin(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── List / get ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_volumes(
    standalone: Optional[bool] = Query(None, description="If true, return only volumes not in any collection"),
    db=Depends(get_db),
):
    if standalone:
        rows = db.execute(
            "SELECT * FROM volumes WHERE collection_id IS NULL ORDER BY institution, title"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM volumes ORDER BY institution, title"
        ).fetchall()

    result = []
    for r in rows:
        vol = dict(r)
        if vol.get("collection_id"):
            coll = db.execute("""
                SELECT c.slug, c.title,
                       COUNT(v2.id) AS volume_count
                FROM collections c
                LEFT JOIN volumes v2 ON v2.collection_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
            """, (vol["collection_id"],)).fetchone()
            vol["collection"] = dict(coll) if coll else None
        else:
            vol["collection"] = None
        result.append(vol)
    return result


@router.get("/{slug}")
async def get_volume(slug: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM volumes WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Volume not found")
    return dict(row)


@router.get("/{slug}/canvases")
async def get_volume_canvases(slug: str, db=Depends(get_db)):
    """Return canvas list (id, label, thumbnail URL) for a volume."""
    row = db.execute(
        "SELECT manifest_url FROM volumes WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Volume not found")

    manifest_url = row["manifest_url"]
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(
                manifest_url,
                headers={"Accept": "application/ld+json,application/json;q=0.9"},
            )
            resp.raise_for_status()
            manifest = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch manifest: {e}")

    canvases = _extract_canvases(manifest)
    return {"slug": slug, "manifest_url": manifest_url, "canvases": canvases}


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    manifest_url: str
    institution: str
    slug_prefix: str
    slug_suffix: str | None = None  # override; auto-generated if omitted


@router.post("/")
async def ingest_manifest(
    request: Request,
    data: IngestRequest,
    db=Depends(get_db),
):
    require_admin(request)

    # Fetch and parse the manifest
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(
                data.manifest_url,
                headers={"Accept": "application/ld+json,application/json;q=0.9"},
            )
            resp.raise_for_status()
            manifest = resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Upstream returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch manifest: {e}")

    meta = _extract_manifest_metadata(manifest, data.manifest_url)

    # Build slug
    if data.slug_suffix:
        slug = f"{data.slug_prefix}-{data.slug_suffix}"
    else:
        # Use last path segment of URL as suffix
        path = urlparse(data.manifest_url).path.rstrip("/")
        suffix = path.split("/")[-1] or path.split("/")[-2]
        # Strip percent-encoding markers common in ARK URLs
        suffix = suffix.replace("%3A", "-").replace("%2F", "-").replace("ark-", "")
        slug = f"{data.slug_prefix}-{suffix}"

    user = request.session.get("user", {})

    try:
        db.execute(
            """INSERT INTO volumes
               (slug, manifest_url, institution, title, title_local,
                thumbnail, date_label, genre, language, canvas_count, added_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                slug,
                data.manifest_url,
                data.institution,
                meta["title"],
                meta.get("title_local"),
                meta.get("thumbnail"),
                meta.get("date_label"),
                meta.get("genre"),
                meta.get("language"),
                meta.get("canvas_count"),
                user.get("orcid"),
            ),
        )
        db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail="A volume with this manifest URL or slug already exists")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "slug": slug,
        "manifest_url": data.manifest_url,
        "title": meta["title"],
        "canvas_count": meta.get("canvas_count"),
    }


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{slug}")
async def delete_volume(slug: str, request: Request, db=Depends(get_db)):
    require_admin(request)
    row = db.execute("SELECT id FROM volumes WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Volume not found")
    db.execute("DELETE FROM volumes WHERE slug = ?", (slug,))
    db.commit()
    return {"deleted": slug}


# ── Manifest parsing helpers ──────────────────────────────────────────────────

def _label_value(label_obj) -> str:
    """Extract a string from a IIIF v2 or v3 label."""
    if isinstance(label_obj, str):
        return label_obj
    if isinstance(label_obj, list):
        return label_obj[0] if label_obj else ""
    if isinstance(label_obj, dict):
        for lang in ("none", "en", "ja", "ja-Latn"):
            if lang in label_obj:
                v = label_obj[lang]
                return v[0] if isinstance(v, list) else str(v)
        # fallback: first value in dict
        for v in label_obj.values():
            return v[0] if isinstance(v, list) else str(v)
    return ""


def _ensure_image_url(url: str | None) -> str | None:
    """If url looks like a bare IIIF image service ID, append image path params."""
    if not url:
        return url
    if "/iiif/2/" in url and "/full/" not in url and not url.lower().endswith((".jpg", ".png", ".gif")):
        return url.rstrip("/") + "/full/80,/0/default.jpg"
    return url


def _extract_manifest_metadata(manifest: dict, manifest_url: str) -> dict:
    ctx = manifest.get("@context", "")
    is_v3 = "presentation/3" in ctx or manifest.get("type") == "Manifest"

    title = _label_value(manifest.get("label", ""))
    if not title:
        title = manifest_url

    # Thumbnail
    thumbnail = None
    thumb = manifest.get("thumbnail")
    if isinstance(thumb, list) and thumb:
        thumb = thumb[0]
    if isinstance(thumb, dict):
        thumbnail = thumb.get("id") or thumb.get("@id")
    elif isinstance(thumb, str):
        thumbnail = thumb
    thumbnail = _ensure_image_url(thumbnail)

    # Canvas count
    if is_v3:
        canvases = manifest.get("items", [])
    else:
        canvases = manifest.get("sequences", [{}])[0].get("canvases", []) if manifest.get("sequences") else []
    canvas_count = len(canvases)

    # If no thumbnail from manifest, build one from first canvas image service
    if not thumbnail and canvases:
        thumbnail = _thumbnail_from_canvas(canvases[0], is_v3)

    # Metadata fields
    date_label = None
    genre = None
    language = manifest.get("language") or manifest.get("@language")
    if isinstance(language, list):
        language = language[0] if language else None

    for item in manifest.get("metadata", []):
        label = _label_value(item.get("label", "")).lower()
        value = _label_value(item.get("value", ""))
        if any(k in label for k in ("date", "year")):
            date_label = value
        if "genre" in label or "form" in label:
            genre = value
        if "language" in label and not language:
            language = value

    return {
        "title": title,
        "thumbnail": thumbnail,
        "canvas_count": canvas_count,
        "date_label": date_label,
        "genre": genre,
        "language": language,
    }


def _thumbnail_from_canvas(canvas: dict, is_v3: bool) -> str | None:
    """Build an 80px thumbnail URL from a canvas's image service."""
    try:
        if is_v3:
            for annotation_page in canvas.get("items", []):
                for annotation in annotation_page.get("items", []):
                    body = annotation.get("body", {})
                    if isinstance(body, list):
                        body = body[0]
                    service = body.get("service")
                    if isinstance(service, list):
                        service = service[0]
                    if isinstance(service, dict):
                        svc_id = service.get("id") or service.get("@id", "")
                        if svc_id:
                            return f"{svc_id.rstrip('/')}/full/80,/0/default.jpg"
        else:
            images = canvas.get("images", [])
            if images:
                resource = images[0].get("resource", {})
                service = resource.get("service", {})
                svc_id = service.get("@id", "") if isinstance(service, dict) else ""
                if svc_id:
                    return f"{svc_id.rstrip('/')}/full/80,/0/default.jpg"
    except Exception:
        pass
    return None


def _extract_canvases(manifest: dict) -> list:
    """Return list of {id, label, thumbnail} for each canvas."""
    ctx = manifest.get("@context", "")
    is_v3 = "presentation/3" in ctx or manifest.get("type") == "Manifest"

    if is_v3:
        raw = manifest.get("items", [])
    else:
        raw = manifest.get("sequences", [{}])[0].get("canvases", []) if manifest.get("sequences") else []

    result = []
    for canvas in raw:
        canvas_id = canvas.get("id") or canvas.get("@id", "")
        label = _label_value(canvas.get("label", ""))
        thumbnail = _thumbnail_from_canvas(canvas, is_v3)
        result.append({"id": canvas_id, "label": label, "thumbnail": thumbnail})
    return result
