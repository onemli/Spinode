import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "spinode.db"

SCHEMA_VERSION = 3

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("PRAGMA user_version;")
    ver = cur.fetchone()[0] or 0

    # base tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY,
        module TEXT,
        name TEXT UNIQUE,
        label TEXT,
        category TEXT,
        rn_format TEXT,
        naming_props_csv TEXT,
        descr TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS props (
        id INTEGER PRIMARY KEY,
        class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
        name TEXT,
        descr TEXT,
        is_naming INTEGER DEFAULT 0,
        is_config INTEGER DEFAULT 0,
        ptype TEXT,
        regex TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS relations (
        id INTEGER PRIMARY KEY,
        src_class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
        rel_type TEXT,                -- child | parent | rs | rt
        dst_name TEXT,                -- geçici: sınıf adı
        dst_class_id INTEGER,         -- 2. geçişte doldurulur
        cardinality TEXT,
        descr TEXT
    );
    """)
    # NEW: prop sabitleri (enum) için tablo
    cur.execute("""
    CREATE TABLE IF NOT EXISTS prop_enums (
        id INTEGER PRIMARY KEY,
        class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
        prop_name TEXT,
        const_name TEXT,
        const_label TEXT,
        const_value TEXT
    );
    """)

    # NEW: deployment path'ler
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deployment_paths (
        id INTEGER PRIMARY KEY,
        class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
        name TEXT,
        descr TEXT,
        target_class TEXT
    );
    """)

    # (duplicate prop’ları önlemek için) benzersiz index — eğer yoksa
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_props_class_name ON props(class_id, name);")

    # NEW: query logları
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY,
        user TEXT,
        class_name TEXT,
        command TEXT,
        status TEXT,
        error_text TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_logs_created_at ON logs(created_at DESC);")

    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS class_fts
    USING fts5(content, tokenize='unicode61');
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_src ON relations(src_class_id);")

    # add missing columns for older DBs (safe migrations)
    _safe_add_column(cur, "classes", "rn_format", "TEXT")
    _safe_add_column(cur, "classes", "naming_props_csv", "TEXT")
    _safe_add_column(cur, "props", "is_naming", "INTEGER DEFAULT 0")
    _safe_add_column(cur, "props", "is_config", "INTEGER DEFAULT 0")
    _safe_add_column(cur, "props", "ptype", "TEXT")
    _safe_add_column(cur, "props", "regex", "TEXT")

    if ver < SCHEMA_VERSION:
        cur.execute(f"PRAGMA user_version={SCHEMA_VERSION};")

    conn.commit(); conn.close()


def _safe_add_column(cur, table: str, col: str, decl: str):
    cur.execute(f"PRAGMA table_info({table});")
    cols = {r[1] for r in cur.fetchall()}
    if col not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl};")


def rebuild_fts():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM class_fts;")
    cur.execute("""
    SELECT c.id, c.name, COALESCE(c.label,''), COALESCE(c.category,''), COALESCE(c.descr,''),
           COALESCE(c.rn_format,''), COALESCE(c.naming_props_csv,''),
           COALESCE((SELECT GROUP_CONCAT(p.name, ' ') FROM props p WHERE p.class_id=c.id), '')
    FROM classes c;
    """)
    for r in cur.fetchall():
        content = " ".join([r[1], r[2], r[3], r[4], r[5], r[6], r[7]]).strip()
        cur.execute("INSERT INTO class_fts(rowid, content) VALUES(?, ?);", (r[0], content))
    conn.commit(); conn.close()
