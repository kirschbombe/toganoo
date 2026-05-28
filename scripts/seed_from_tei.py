"""
seed_from_tei.py

Imports provenance annotations from Hiro's TEI files into the annotation database.
Each <seal> and <provenance><p> element becomes one annotation record.

Since the TEI files don't include canvas IDs or image region coordinates,
annotations are seeded with:
  - canvas_id:   first canvas of the manifest (fetched live)
  - region_xywh: pixel:0,0,1,1  (placeholder — scholars should update via the UI)

Usage (from project root):
    python scripts/seed_from_tei.py

Or inside Docker:
    docker compose exec app python scripts/seed_from_tei.py
"""

import os
import sys
import uuid
import sqlite3
import urllib.request
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH  = os.getenv("DB_PATH", "data/annotations.db")
TEI_DIR  = Path("data/tei")

HIRO_ORCID = "https://orcid.org/0000-0000-0000-HIRO"   # placeholder until real iD known
HIRO_NAME  = "Hiroyuki Ikuura (seeded from TEI)"

NS = {"tei": "http://www.tei-c.org/ns/1.0"}

# ── ARK map ───────────────────────────────────────────────────────────────────
# TEI container number → volume ARK and manifest URL
# Multi-part works (7098, 7099) map to individual volume ARKs where identified.
# 7366 not yet matched; included with placeholder ARK.

TEI_MAP = {
    "7044.xml":  {
        "ark": "ark:/21198/n1mk86",
        "manifest": "http://iiif.library.ucla.edu/ark%3A%2F21198%2Fn1mk86/manifest",
        "title": "Ōri Daijō denzū yōroku",
    },
    "7051.xml":  {
        "ark": "ark:/21198/n1kk7h",
        "manifest": "http://iiif.library.ucla.edu/ark%3A%2F21198%2Fn1kk7h/manifest",
        "title": "Mitsuzō yōgi",
    },
    "7098上.xml": {
        "ark": "ark:/21198/z14c09rh",     # collection-level; volume ARK TBD
        "manifest": None,
        "title": "Hōsokushū (上)",
    },
    "7098下.xml": {
        "ark": "ark:/21198/z14c09rh",
        "manifest": None,
        "title": "Hōsokushū (下)",
    },
    "7099上.xml": {
        "ark": "ark:/21198/z18412fs",
        "manifest": None,
        "title": "Hizō hōyaku mondanshō (上)",
    },
    "7099下.xml": {
        "ark": "ark:/21198/z18412fs",
        "manifest": None,
        "title": "Hizō hōyaku mondanshō (下)",
    },
    "7221.xml":  {
        "ark": "ark:/21198/n1q90b",
        "manifest": "http://iiif.library.ucla.edu/ark%3A%2F21198%2Fn1q90b/manifest",
        "title": "Mitsurin yozai",
    },
    "7358.xml":  {
        "ark": "ark:/21198/n1gs4h",
        "manifest": "http://iiif.library.ucla.edu/ark%3A%2F21198%2Fn1gs4h/manifest",
        "title": "Himitsu mandarakyō kaien genjo",
    },
    "7366.xml":  {
        "ark": "ark:/21198/n1UNKNOWN7366",   # ARK not yet matched
        "manifest": None,
        "title": "Unknown (7366)",
    },
}


# ── Manifest fetch ────────────────────────────────────────────────────────────

def get_first_canvas_id(manifest_url):
    """Fetch a IIIF manifest and return the first canvas ID."""
    if not manifest_url:
        return None
    try:
        req = urllib.request.Request(
            manifest_url,
            headers={"Accept": "application/json, application/ld+json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            manifest = json.loads(r.read())
        # v2
        canvases = manifest.get("sequences", [{}])[0].get("canvases", [])
        if canvases:
            return canvases[0].get("@id")
        # v3
        items = manifest.get("items", [])
        if items:
            return items[0].get("id") or items[0].get("@id")
    except Exception as e:
        print(f"    Warning: could not fetch manifest ({e})")
    return None


# ── TEI parsing ───────────────────────────────────────────────────────────────

def innertext(el):
    """Get all text content from an element and its children."""
    return "".join(el.itertext()).strip()


def extract_entity(prov_p, tag):
    """Extract named entity text from a provenance <p> element."""
    found = []
    for child in prov_p.findall(f"tei:{tag}", NS):
        t = innertext(child).strip()
        if t:
            found.append(t)
    return "、".join(found) if found else ""


def location_from_text(text):
    """Guess location_on_object from free text."""
    text = text.lower()
    if "front cover" in text or "表紙" in text:
        return "front-cover"
    if "back cover" in text:
        return "back-cover"
    if "spine" in text:
        return "spine"
    if "first" in text and "leaf" in text:
        return "first-leaf-recto"
    if "last" in text and "leaf" in text:
        return "last-leaf-recto"
    if "end paper" in text or "endpaper" in text:
        return "endpaper-back"
    if "title" in text:
        return "title-slip"
    return "other"


def mark_type_from_text(text):
    """Guess mark type from free text."""
    text = text.lower()
    if "collector" in text or "seal" in text or "蔵書印" in text:
        return "collectors-seal"
    if "sticker" in text or "label" in text:
        return "sticker-label"
    if "written" in text or "writing" in text or "inscription" in text:
        return "handwritten-inscription"
    if "stamp" in text:
        return "institutional-stamp"
    return "handwritten-inscription"


def parse_tei_file(path):
    """Parse a TEI file and return a list of annotation dicts."""
    annotations = []

    # 7044 has malformed XML — patch it
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r'<hasWitness[^/]*/>', '', raw)   # remove orphan tag
    raw = re.sub(r'<hasWitness[^>]*>', '', raw)

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"    XML parse error: {e} — skipping")
        return []

    # ── Structured <seal> elements ────────────────────────────────────────────
    for seal in root.findall(".//tei:sealDesc/tei:seal", NS):
        seal_type = seal.get("type", "sticker-label")
        mark_type = {
            "sticker":          "sticker-label",
            "collectors-seal":  "collectors-seal",
            "institutional":    "institutional-stamp",
        }.get(seal_type, "sticker-label")

        deco = {d.get("type"): d.text for d in seal.findall("tei:decoNote", NS)}
        ab   = seal.find("tei:ab", NS)
        note = seal.find("tei:note", NS)
        p    = seal.find("tei:p", NS)

        transcription = innertext(ab) if ab is not None else (innertext(p) if p is not None else "")
        location      = note.text.strip() if note is not None else "other"
        location_v    = location_from_text(location)

        annotations.append({
            "mark_type":         mark_type,
            "shape":             deco.get("shape"),
            "ink_color":         deco.get("color"),
            "script_type":       deco.get("script"),
            "condition":         deco.get("condition", "clear"),
            "transcription":     transcription,
            "transcription_rom": None,
            "owner_name":        None,
            "owner_type":        None,
            "place_name":        None,
            "location_on_object": location_v,
            "notes":             f"Seeded from TEI (Hiroyuki Ikuura). Location note: \"{location}\"",
        })

    # ── Unstructured <provenance><p> elements ─────────────────────────────────
    for prov in root.findall(".//tei:history/tei:provenance", NS):
        for p in prov.findall("tei:p", NS):
            full_text = innertext(p).strip()
            if not full_text or full_text == '"':
                continue

            org_name  = extract_entity(p, "orgName")
            pers_name = extract_entity(p, "persName")
            place     = extract_entity(p, "placeName")

            mark_type = mark_type_from_text(full_text)
            location  = location_from_text(full_text)

            # Extract quoted text as transcription
            quoted = re.findall(r'"([^"]+)"', full_text)
            transcription = quoted[0] if quoted else ""

            owner_name = org_name or pers_name or None
            owner_type = "temple" if org_name else ("person" if pers_name else None)

            annotations.append({
                "mark_type":          mark_type,
                "shape":              None,
                "ink_color":          None,
                "script_type":        None,
                "condition":          "clear",
                "transcription":      transcription,
                "transcription_rom":  None,
                "owner_name":         owner_name,
                "owner_type":         owner_type,
                "place_name":         place or None,
                "location_on_object": location,
                "notes":              f"Seeded from TEI (Hiroyuki Ikuura). Full text: {full_text[:200]}",
            })

    return annotations


# ── Database ──────────────────────────────────────────────────────────────────

def seed():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Ensure tables exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS annotations (
            id TEXT PRIMARY KEY, volume_ark TEXT NOT NULL,
            canvas_id TEXT NOT NULL, canvas_label TEXT,
            region_xywh TEXT NOT NULL, mark_type TEXT NOT NULL,
            shape TEXT, ink_color TEXT, script_type TEXT, condition TEXT,
            transcription TEXT, transcription_rom TEXT,
            owner_name TEXT, owner_type TEXT, owner_authority_uri TEXT,
            place_name TEXT, place_authority_uri TEXT,
            location_on_object TEXT, notes TEXT,
            annotator_orcid TEXT NOT NULL, annotator_name TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY (annotator_orcid) REFERENCES users(id)
        );
    """)

    # Insert Hiro as a user
    conn.execute(
        "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
        (HIRO_ORCID, HIRO_NAME),
    )
    conn.commit()

    total = 0
    for filename, meta in TEI_MAP.items():
        path = TEI_DIR / filename
        if not path.exists():
            print(f"  Skipping {filename} — not found")
            continue

        print(f"\n{filename} → {meta['title']}")

        # Fetch first canvas ID
        canvas_id = get_first_canvas_id(meta["manifest"])
        if canvas_id:
            print(f"  Canvas: {canvas_id}")
        else:
            canvas_id = f"PLACEHOLDER:{meta['ark']}"
            print(f"  Canvas: placeholder (manifest unavailable)")

        annotations = parse_tei_file(path)
        print(f"  Parsed {len(annotations)} marks")

        # Skip if already seeded for this volume
        existing = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE volume_ark=? AND annotator_orcid=?",
            (meta["ark"], HIRO_ORCID),
        ).fetchone()[0]
        if existing:
            print(f"  Already seeded ({existing} records) — skipping")
            continue

        now = datetime.now(timezone.utc).isoformat()
        for a in annotations:
            conn.execute(
                """INSERT INTO annotations (
                    id, volume_ark, canvas_id, canvas_label, region_xywh,
                    mark_type, shape, ink_color, script_type, condition,
                    transcription, transcription_rom,
                    owner_name, owner_type, owner_authority_uri,
                    place_name, place_authority_uri,
                    location_on_object, notes,
                    annotator_orcid, annotator_name, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), meta["ark"], canvas_id, "front cover",
                    "pixel:0,0,1,1",
                    a["mark_type"], a["shape"], a["ink_color"],
                    a["script_type"], a["condition"],
                    a["transcription"], a["transcription_rom"],
                    a["owner_name"], a["owner_type"], None,
                    a["place_name"], None,
                    a["location_on_object"], a["notes"],
                    HIRO_ORCID, HIRO_NAME, now, now,
                ),
            )
            total += 1

        conn.commit()
        print(f"  Inserted {len(annotations)} annotations")

    conn.close()
    print(f"\nDone — {total} annotations seeded total")


if __name__ == "__main__":
    # Allow running from project root or from scripts/
    if not Path("data").exists():
        os.chdir(Path(__file__).parent.parent)
    seed()
