import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/annotations.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS annotations (
            id                   TEXT PRIMARY KEY,
            volume_ark           TEXT NOT NULL,
            canvas_id            TEXT NOT NULL,
            canvas_label         TEXT,
            region_xywh          TEXT NOT NULL,
            mark_type            TEXT NOT NULL,
            shape                TEXT,
            ink_color            TEXT,
            script_type          TEXT,
            condition            TEXT,
            transcription        TEXT,
            transcription_rom    TEXT,
            owner_name           TEXT,
            owner_type           TEXT,
            owner_authority_uri  TEXT,
            place_name           TEXT,
            place_authority_uri  TEXT,
            location_on_object   TEXT,
            notes                TEXT,
            annotator_orcid      TEXT NOT NULL,
            annotator_name       TEXT,
            created_at           TEXT NOT NULL,
            updated_at           TEXT NOT NULL,
            FOREIGN KEY (annotator_orcid) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()
