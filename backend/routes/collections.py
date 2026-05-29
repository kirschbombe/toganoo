from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..database import get_db
from .volumes import _extract_manifest_metadata, _label_value, require_admin

router = APIRouter()


# ── List / get ────────────────────────────────────────────────────────────────

@router.get("/")
async def list_collections(db=Depends(get_db)):
    rows = db.execute("""
        SELECT c.*,
               COUNT(v.id)                                   AS volume_count,
               MIN(CASE WHEN v.volume_number = (
                   SELECT MIN(v2.volume_number) FROM volumes v2 WHERE v2.collection_id = c.id
               ) THEN v.slug END)                            AS first_volume_slug
        FROM collections c
        LEFT JOIN volumes v ON v.collection_id = c.id
        GROUP BY c.id
        ORDER BY c.institution, c.title
    """).fetchall()
    return [dict(r) for r in rows]


@router.get("/{slug}")
async def get_collection(slug: str, db=Depends(get_db)):
    coll = db.execute(
        "SELECT * FROM collections WHERE slug = ?", (slug,)
    ).fetchone()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    volumes = db.execute("""
        SELECT id, slug, title, title_local, thumbnail, manifest_url,
               volume_number, volume_label, institution, canvas_count
        FROM volumes
        WHERE collection_id = ?
        ORDER BY volume_number
    """, (coll["id"],)).fetchall()

    return {**dict(coll), "volumes": [dict(v) for v in volumes]}


@router.get("/{slug}/annotations")
async def get_collection_annotations(slug: str, db=Depends(get_db)):
    """All annotations for every volume in the collection, grouped by volume."""
    coll = db.execute(
        "SELECT id FROM collections WHERE slug = ?", (slug,)
    ).fetchone()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")

    volumes = db.execute("""
        SELECT id, slug, title, volume_number, volume_label, manifest_url
        FROM volumes
        WHERE collection_id = ?
        ORDER BY volume_number
    """, (coll["id"],)).fetchall()

    result = []
    for vol in volumes:
        annotations = db.execute(
            "SELECT * FROM annotations WHERE volume_id = ? ORDER BY created_at",
            (vol["manifest_url"],)
        ).fetchall()
        result.append({
            "volume_slug":   vol["slug"],
            "volume_title":  vol["title"],
            "volume_number": vol["volume_number"],
            "volume_label":  vol["volume_label"],
            "annotations":   [dict(a) for a in annotations],
        })
    return result


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestCollectionRequest(BaseModel):
    collection_url: str
    institution:    str
    slug_prefix:    str


@router.post("/")
async def ingest_collection(
    request: Request,
    data: IngestCollectionRequest,
    db=Depends(get_db),
):
    require_admin(request)
    user = request.session.get("user", {})

    # Fetch the Collection document
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(
                data.collection_url,
                headers={"Accept": "application/ld+json,application/json;q=0.9"},
            )
            resp.raise_for_status()
            collection_doc = resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Upstream returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch collection: {e}")

    # Detect version and extract member manifest references
    ctx  = collection_doc.get("@context", "")
    is_v3 = "presentation/3" in ctx or collection_doc.get("type") == "Collection"

    members = _extract_collection_members(collection_doc, is_v3)
    if not members:
        raise HTTPException(status_code=422, detail="No manifest items found in collection document")

    # Collection-level title and thumbnail
    coll_title = _label_value(collection_doc.get("label", "")) or data.collection_url
    coll_title_local = None
    if isinstance(collection_doc.get("label"), dict):
        for lang in ("ja", "zh", "ko"):
            if lang in collection_doc["label"]:
                v = collection_doc["label"][lang]
                coll_title_local = v[0] if isinstance(v, list) else str(v)
                break

    # Generate collection slug
    path   = urlparse(data.collection_url).path.rstrip("/")
    suffix = path.split("/")[-1] or path.split("/")[-2]
    suffix = suffix.replace("%3A", "-").replace("%2F", "-").replace("ark-", "")
    coll_slug = f"{data.slug_prefix}-{suffix}"

    # Insert collection record
    try:
        db.execute("""
            INSERT INTO collections (slug, collection_url, institution, title, title_local)
            VALUES (?,?,?,?,?)
        """, (coll_slug, data.collection_url, data.institution, coll_title, coll_title_local))
        db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail="A collection with this URL or slug already exists")
        raise HTTPException(status_code=500, detail=str(e))

    coll_id = db.execute(
        "SELECT id FROM collections WHERE slug = ?", (coll_slug,)
    ).fetchone()["id"]

    # Fetch and ingest each member manifest
    ingested = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        for i, member in enumerate(members):
            manifest_url  = member["id"]
            member_label  = member.get("label", "")

            try:
                resp = await client.get(
                    manifest_url,
                    headers={"Accept": "application/ld+json,application/json;q=0.9"},
                )
                resp.raise_for_status()
                manifest = resp.json()
                meta = _extract_manifest_metadata(manifest, manifest_url)
            except Exception:
                # Use whatever we have from the collection doc if the fetch fails
                meta = {
                    "title":        _label_value(member_label) or manifest_url,
                    "thumbnail":    None,
                    "canvas_count": None,
                    "date_label":   None,
                    "genre":        None,
                    "language":     None,
                }

            # Slug for this volume
            mpath  = urlparse(manifest_url).path.rstrip("/")
            msuffix = mpath.split("/")[-1] or mpath.split("/")[-2]
            msuffix = msuffix.replace("%3A", "-").replace("%2F", "-").replace("ark-", "")
            vol_slug = f"{data.slug_prefix}-{msuffix}"

            vol_label = _label_value(member_label) if member_label else f"Volume {i + 1}"

            # Use first volume thumbnail as collection thumbnail
            if i == 0 and meta.get("thumbnail"):
                db.execute(
                    "UPDATE collections SET thumbnail = ? WHERE id = ?",
                    (meta["thumbnail"], coll_id)
                )

            try:
                db.execute("""
                    INSERT INTO volumes
                    (slug, manifest_url, institution, title, title_local,
                     thumbnail, date_label, genre, language, canvas_count,
                     collection_id, volume_number, volume_label, added_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    vol_slug,
                    manifest_url,
                    data.institution,
                    meta["title"],
                    None,
                    meta.get("thumbnail"),
                    meta.get("date_label"),
                    meta.get("genre"),
                    meta.get("language"),
                    meta.get("canvas_count"),
                    coll_id,
                    i + 1,
                    vol_label,
                    user.get("orcid"),
                ))
                db.commit()
                ingested.append({"slug": vol_slug, "title": meta["title"]})
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    # Volume already exists — link it to this collection
                    db.execute("""
                        UPDATE volumes
                        SET collection_id = ?, volume_number = ?, volume_label = ?
                        WHERE manifest_url = ?
                    """, (coll_id, i + 1, vol_label, manifest_url))
                    db.commit()
                    existing = db.execute(
                        "SELECT slug, title FROM volumes WHERE manifest_url = ?",
                        (manifest_url,)
                    ).fetchone()
                    ingested.append({"slug": existing["slug"], "title": existing["title"]})

    return {
        "collection_slug": coll_slug,
        "title":           coll_title,
        "volumes_ingested": len(ingested),
        "volumes":          ingested,
    }


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{slug}")
async def delete_collection(slug: str, request: Request, db=Depends(get_db)):
    require_admin(request)
    row = db.execute(
        "SELECT id FROM collections WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Unlink volumes (don't delete them — they have annotations)
    db.execute(
        "UPDATE volumes SET collection_id = NULL, volume_number = 0, volume_label = NULL WHERE collection_id = ?",
        (row["id"],)
    )
    db.execute("DELETE FROM collections WHERE id = ?", (row["id"],))
    db.commit()
    return {"deleted": slug}


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _extract_collection_members(doc: dict, is_v3: bool) -> list[dict]:
    """Return list of {id, label} for each Manifest member of the Collection."""
    members = []

    if is_v3:
        for item in doc.get("items", []):
            if item.get("type") == "Manifest":
                members.append({
                    "id":    item.get("id", ""),
                    "label": item.get("label", ""),
                })
            # Recurse one level into nested Collections
            elif item.get("type") == "Collection":
                for sub in item.get("items", []):
                    if sub.get("type") == "Manifest":
                        members.append({
                            "id":    sub.get("id", ""),
                            "label": sub.get("label", ""),
                        })
    else:
        # v2: items in `manifests` array
        for item in doc.get("manifests", []):
            members.append({
                "id":    item.get("@id", ""),
                "label": item.get("label", ""),
            })

    return [m for m in members if m["id"]]
