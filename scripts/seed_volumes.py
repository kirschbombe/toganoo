"""
Seed the volumes table from frontend/data/volumes.json.
Run once after the DB schema migration:

    docker compose exec app python scripts/seed_volumes.py
"""

import json
import os
import sqlite3
from urllib.parse import urlparse

DB_PATH = os.getenv("DB_PATH", "data/annotations.db")
VOLUMES_JSON = os.path.join(os.path.dirname(__file__), "../frontend/data/volumes.json")


def ark_to_suffix(ark: str) -> str:
    """Turn 'ark:/21198/n1mk86' into 'n1mk86'."""
    return ark.rstrip("/").split("/")[-1]


def main():
    with open(VOLUMES_JSON) as f:
        volumes = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    inserted = 0
    skipped = 0

    for v in volumes:
        manifest_url = v.get("manifestUrl", "")
        if not manifest_url:
            print(f"  SKIP (no manifestUrl): {v.get('title')}")
            skipped += 1
            continue

        ark = v.get("ark", "")
        suffix = ark_to_suffix(ark) if ark else urlparse(manifest_url).path.split("/")[-1]
        slug = f"ucla-{suffix}"

        title = v.get("title") or v.get("titleJa") or manifest_url
        title_local = v.get("titleJa") or None

        # Prefer dateNormalized; fall back to raw dateCreation (may contain "|~|" separators)
        date_label = v.get("dateNormalized") or (v.get("dateCreation", "").split("|~|")[0].strip() or None)

        try:
            conn.execute(
                """INSERT OR IGNORE INTO volumes
                   (slug, manifest_url, institution, title, title_local,
                    thumbnail, date_label, genre, language)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    slug,
                    manifest_url,
                    "UCLA Library",
                    title,
                    title_local,
                    v.get("thumbnail"),
                    date_label,
                    v.get("genre") or None,
                    v.get("language") or None,
                ),
            )
            if conn.execute("SELECT changes()").fetchone()[0]:
                print(f"  INSERT: {slug} — {title[:60]}")
                inserted += 1
            else:
                print(f"  EXISTS: {slug}")
                skipped += 1
        except Exception as e:
            print(f"  ERROR ({slug}): {e}")
            skipped += 1

    conn.commit()
    conn.close()
    print(f"\nDone: {inserted} inserted, {skipped} skipped/existing.")


if __name__ == "__main__":
    main()
