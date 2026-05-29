import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/annotations.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    # Step 1: create tables (no indexes on columns that may need renaming)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            institution TEXT,
            is_admin    INTEGER DEFAULT 0,
            is_editor   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS collections (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            slug           TEXT UNIQUE NOT NULL,
            collection_url TEXT UNIQUE,
            institution    TEXT NOT NULL,
            title          TEXT NOT NULL,
            title_local    TEXT,
            thumbnail      TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS volumes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            slug          TEXT UNIQUE NOT NULL,
            manifest_url  TEXT UNIQUE NOT NULL,
            institution   TEXT NOT NULL,
            title         TEXT NOT NULL,
            title_local   TEXT,
            thumbnail     TEXT,
            date_label    TEXT,
            genre         TEXT,
            language      TEXT,
            canvas_count  INTEGER,
            collection_id INTEGER REFERENCES collections(id),
            volume_number INTEGER DEFAULT 0,
            volume_label  TEXT,
            added_by      TEXT REFERENCES users(id),
            created_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS annotations (
            id                   TEXT PRIMARY KEY,
            volume_id            TEXT NOT NULL,
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

    # Step 2: migrate existing schema (renames volume_ark → volume_id, adds columns, etc.)
    _migrate(conn)

    # Step 3: create indexes now that column names are stable
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_collections_slug    ON collections(slug);
        CREATE INDEX IF NOT EXISTS idx_volumes_institution ON volumes(institution);
        CREATE INDEX IF NOT EXISTS idx_volumes_slug        ON volumes(slug);
        CREATE INDEX IF NOT EXISTS idx_volumes_collection  ON volumes(collection_id);
        CREATE INDEX IF NOT EXISTS idx_annotations_volume  ON annotations(volume_id);
        CREATE INDEX IF NOT EXISTS idx_annotations_canvas  ON annotations(canvas_id, volume_id);
    """)
    conn.commit()
    conn.close()


def _migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]

    if version < 1:
        # Add institution and is_admin to existing users table
        existing = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "institution" not in existing:
            conn.execute("ALTER TABLE users ADD COLUMN institution TEXT")
        if "is_admin" not in existing:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

        # Rename volume_ark → volume_id in annotations (SQLite 3.25+)
        anno_cols = {row[1] for row in conn.execute("PRAGMA table_info(annotations)")}
        if "volume_ark" in anno_cols and "volume_id" not in anno_cols:
            conn.execute("ALTER TABLE annotations RENAME COLUMN volume_ark TO volume_id")

        # Create volumes table if it didn't exist yet (older DBs)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volumes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                slug         TEXT UNIQUE NOT NULL,
                manifest_url TEXT UNIQUE NOT NULL,
                institution  TEXT NOT NULL,
                title        TEXT NOT NULL,
                title_local  TEXT,
                thumbnail    TEXT,
                date_label   TEXT,
                genre        TEXT,
                language     TEXT,
                canvas_count INTEGER,
                added_by     TEXT REFERENCES users(id),
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.execute("PRAGMA user_version = 1")
        conn.commit()

    if version < 2:
        # Add collections table (may already exist on fresh installs)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                slug           TEXT UNIQUE NOT NULL,
                collection_url TEXT UNIQUE,
                institution    TEXT NOT NULL,
                title          TEXT NOT NULL,
                title_local    TEXT,
                thumbnail      TEXT,
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)

        # Add collection columns to volumes
        vol_cols = {row[1] for row in conn.execute("PRAGMA table_info(volumes)")}
        if "collection_id" not in vol_cols:
            conn.execute("ALTER TABLE volumes ADD COLUMN collection_id INTEGER REFERENCES collections(id)")
        if "volume_number" not in vol_cols:
            conn.execute("ALTER TABLE volumes ADD COLUMN volume_number INTEGER DEFAULT 0")
        if "volume_label" not in vol_cols:
            conn.execute("ALTER TABLE volumes ADD COLUMN volume_label TEXT")

        conn.commit()
        conn.execute("PRAGMA user_version = 2")
        conn.commit()

    if version < 3:
        # Add is_editor role to users
        user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "is_editor" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_editor INTEGER DEFAULT 0")
        # Existing admins implicitly have editor rights, but is_editor is
        # checked separately so admins always pass the editor gate too.
        conn.commit()
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
