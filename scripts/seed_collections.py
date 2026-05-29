"""
Seed multi-volume collections from the works*-multi.csv files.

Usage:
    python scripts/seed_collections.py [path/to/csv ...]

Default: looks for works1-multi.csv and works2-multi.csv next to the script,
         or pass explicit paths.

    docker compose exec app python scripts/seed_collections.py

The script:
  1. Reads each CSV row (IIIF Object Type == "Collection")
  2. Fetches the IIIF Collection document
  3. Inserts a `collections` record
  4. Fetches each member manifest and inserts / links a `volumes` record
  5. Skips rows whose collection_url already exists in the DB
"""

import csv
import os
import re
import sqlite3
import sys
import time
from urllib.parse import urlparse

import httpx

# Ensure the DB schema (including v2 migration) is applied before we touch it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.database import init_db

DB_PATH = os.getenv("DB_PATH", "data/annotations.db")
INSTITUTION = "UCLA Library"
SLUG_PREFIX = "ucla"

# Locate default CSV paths relative to this script
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSVS = [
    os.path.join(_HERE, "../frontend/data/works1-multi.csv"),
    os.path.join(_HERE, "../frontend/data/works2-multi.csv"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def label_value(obj) -> str:
    """Extract plain string from a IIIF v2 or v3 label."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return obj[0] if obj else ""
    if isinstance(obj, dict):
        for lang in ("none", "en", "ja", "ja-Latn"):
            if lang in obj:
                v = obj[lang]
                return v[0] if isinstance(v, list) else str(v)
        first = next(iter(obj.values()), "")
        return first[0] if isinstance(first, list) else str(first)
    return ""


def split_title(raw: str):
    """
    'Hizō hōyaku mondanshō | 秘藏寶鑰問談鈔' → ('Hizō hōyaku mondanshō', '秘藏寶鑰問談鈔')
    Falls back to (raw, None) if no pipe separator.
    """
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|", 1)]
        title = parts[0]
        title_local = parts[1] if parts[1] else None
        return title, title_local
    return raw.strip(), None


def ark_suffix(url: str) -> str:
    """
    Extract a slug-safe suffix from a manifest or collection URL.
    For UCLA URLs like '.../ark%3A%2F21198%2Fn1c339/manifest', the
    last segment is 'manifest' (non-unique), so we use the ARK segment
    before it and pull out just the local identifier.
    """
    path = urlparse(url).path.rstrip("/")
    segments = [s for s in path.split("/") if s]
    # Skip generic trailing segments
    while segments and segments[-1].lower() in ("manifest", "collection", "canvas"):
        segments.pop()
    seg = segments[-1] if segments else "unknown"
    # Percent-decode so we can split on real slashes/colons
    seg = seg.replace("%3A", ":").replace("%2F", "/").replace("%3a", ":")
    # For 'ark:/21198/n1c339', take only the local part
    if "/" in seg:
        seg = seg.split("/")[-1]
    # Remove any remaining special chars
    seg = re.sub(r"[^a-zA-Z0-9-]", "-", seg).strip("-")
    return seg


def ensure_image_url(url):
    """If url is a bare IIIF image service ID, append image path params."""
    if not url:
        return url
    if "/iiif/2/" in url and "/full/" not in url and not url.lower().endswith((".jpg", ".png", ".gif")):
        return url.rstrip("/") + "/full/80,/0/default.jpg"
    return url


def thumbnail_from_canvas(canvas: dict, is_v3: bool):
    try:
        if is_v3:
            for page in canvas.get("items", []):
                for anno in page.get("items", []):
                    body = anno.get("body", {})
                    if isinstance(body, list):
                        body = body[0]
                    svc = body.get("service")
                    if isinstance(svc, list):
                        svc = svc[0]
                    if isinstance(svc, dict):
                        sid = svc.get("id") or svc.get("@id", "")
                        if sid:
                            return f"{sid.rstrip('/')}/full/80,/0/default.jpg"
        else:
            imgs = canvas.get("images", [])
            if imgs:
                res = imgs[0].get("resource", {})
                svc = res.get("service", {})
                sid = svc.get("@id", "") if isinstance(svc, dict) else ""
                if sid:
                    return f"{sid.rstrip('/')}/full/80,/0/default.jpg"
    except Exception:
        pass
    return None


def extract_manifest_meta(manifest: dict, manifest_url: str) -> dict:
    ctx = manifest.get("@context", "")
    is_v3 = "presentation/3" in ctx or manifest.get("type") == "Manifest"

    title = label_value(manifest.get("label", "")) or manifest_url
    thumbnail = None
    thumb = manifest.get("thumbnail")
    if isinstance(thumb, list) and thumb:
        thumb = thumb[0]
    if isinstance(thumb, dict):
        thumbnail = thumb.get("id") or thumb.get("@id")
    elif isinstance(thumb, str):
        thumbnail = thumb

    canvases = manifest.get("items", []) if is_v3 else (
        manifest.get("sequences", [{}])[0].get("canvases", [])
        if manifest.get("sequences") else []
    )
    if not thumbnail and canvases:
        thumbnail = thumbnail_from_canvas(canvases[0], is_v3)

    return {
        "title": title,
        "thumbnail": ensure_image_url(thumbnail),
        "canvas_count": len(canvases),
    }


def extract_collection_members(doc: dict) -> list:
    """Return [{id, label}, ...] for each Manifest in the Collection."""
    ctx = doc.get("@context", "")
    is_v3 = "presentation/3" in ctx or doc.get("type") == "Collection"

    members = []
    if is_v3:
        for item in doc.get("items", []):
            t = item.get("type", "")
            if t == "Manifest":
                members.append({"id": item.get("id", ""), "label": item.get("label", "")})
            elif t == "Collection":
                for sub in item.get("items", []):
                    if sub.get("type") == "Manifest":
                        members.append({"id": sub.get("id", ""), "label": sub.get("label", "")})
    else:
        for item in doc.get("manifests", []):
            members.append({"id": item.get("@id", ""), "label": item.get("label", "")})

    return [m for m in members if m["id"]]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    csv_paths = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_CSVS

    # Gather rows from all CSVs
    rows = []
    for path in csv_paths:
        if not os.path.exists(path):
            print(f"WARNING: CSV not found: {path}")
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url = row.get("IIIF Manifest URL", "").strip()
                obj_type = row.get("IIIF Object Type", "").strip()
                if url and obj_type == "Collection":
                    rows.append(row)

    if not rows:
        print("No Collection rows found in the provided CSVs.")
        return

    print(f"Found {len(rows)} collections to seed.\n")

    # Apply schema migrations before connecting
    init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    ingested = 0
    skipped  = 0

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        for row in rows:
            collection_url = row["IIIF Manifest URL"].strip()
            raw_title = row.get("Title", "").strip()
            title, title_local = split_title(raw_title)
            date_label = row.get("Date.normalized", "").strip() or None
            raw_lang   = row.get("Language", "").strip()
            language   = raw_lang.split("|~|")[0].strip() if raw_lang else None

            # Slug for the collection
            coll_suffix = ark_suffix(collection_url)
            coll_slug   = f"{SLUG_PREFIX}-{coll_suffix}"

            # Skip if collection already exists
            existing = conn.execute(
                "SELECT id FROM collections WHERE collection_url = ? OR slug = ?",
                (collection_url, coll_slug)
            ).fetchone()
            if existing:
                print(f"  EXISTS: {coll_slug} — {title[:60]}")
                skipped += 1
                continue

            print(f"  Fetching collection: {collection_url}")
            try:
                resp = client.get(
                    collection_url,
                    headers={"Accept": "application/ld+json,application/json;q=0.9"},
                )
                resp.raise_for_status()
                coll_doc = resp.json()
            except Exception as e:
                print(f"    ERROR fetching collection: {e}")
                skipped += 1
                continue

            members = extract_collection_members(coll_doc)
            if not members:
                print(f"    ERROR: no manifests found in collection document")
                skipped += 1
                continue

            print(f"    → {len(members)} member manifests")

            # Insert collection record
            try:
                conn.execute("""
                    INSERT INTO collections
                        (slug, collection_url, institution, title, title_local)
                    VALUES (?,?,?,?,?)
                """, (coll_slug, collection_url, INSTITUTION, title, title_local))
                conn.commit()
            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    print(f"    SKIP (duplicate): {coll_slug}")
                    skipped += 1
                    continue
                print(f"    ERROR inserting collection: {e}")
                skipped += 1
                continue

            coll_id = conn.execute(
                "SELECT id FROM collections WHERE slug = ?", (coll_slug,)
            ).fetchone()["id"]

            # Fetch and insert each member manifest
            for i, member in enumerate(members):
                manifest_url  = member["id"]
                member_label  = member.get("label", "")

                # Small delay to be polite to the UCLA server
                time.sleep(0.3)

                try:
                    mresp = client.get(
                        manifest_url,
                        headers={"Accept": "application/ld+json,application/json;q=0.9"},
                    )
                    mresp.raise_for_status()
                    meta = extract_manifest_meta(mresp.json(), manifest_url)
                except Exception as e:
                    print(f"    WARNING: could not fetch manifest {manifest_url}: {e}")
                    meta = {
                        "title": label_value(member_label) or manifest_url,
                        "thumbnail": None,
                        "canvas_count": None,
                    }

                vol_suffix = ark_suffix(manifest_url)
                vol_slug   = f"{SLUG_PREFIX}-{vol_suffix}"
                vol_label  = label_value(member_label) if member_label else f"Volume {i + 1}"

                # Use first volume thumbnail as collection thumbnail
                if i == 0 and meta.get("thumbnail"):
                    conn.execute(
                        "UPDATE collections SET thumbnail = ? WHERE id = ?",
                        (meta["thumbnail"], coll_id)
                    )

                try:
                    conn.execute("""
                        INSERT INTO volumes
                            (slug, manifest_url, institution, title, title_local,
                             thumbnail, date_label, language, canvas_count,
                             collection_id, volume_number, volume_label)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        vol_slug, manifest_url, INSTITUTION,
                        meta["title"], title_local,
                        meta.get("thumbnail"),
                        date_label, language, meta.get("canvas_count"),
                        coll_id, i + 1, vol_label,
                    ))
                    conn.commit()
                    print(f"      INSERT vol {i+1}: {vol_slug} — {meta['title'][:50]}")
                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        # Volume already exists — link it to this collection
                        conn.execute("""
                            UPDATE volumes
                            SET collection_id = ?, volume_number = ?, volume_label = ?
                            WHERE manifest_url = ?
                        """, (coll_id, i + 1, vol_label, manifest_url))
                        conn.commit()
                        existing_vol = conn.execute(
                            "SELECT slug, title FROM volumes WHERE manifest_url = ?",
                            (manifest_url,)
                        ).fetchone()
                        print(f"      LINKED vol {i+1}: {existing_vol['slug']} (already existed)")
                    else:
                        print(f"      ERROR inserting volume {vol_slug}: {e}")

            print(f"  ✓ {coll_slug} — {title[:60]}")
            ingested += 1

    conn.close()
    print(f"\nDone: {ingested} collections ingested, {skipped} skipped/existing.")


if __name__ == "__main__":
    main()
