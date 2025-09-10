from datetime import datetime
from passlib.hash import bcrypt
from core.db import get_conn

def create_user(username: str, password: str, is_admin: bool = False) -> None:
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            last_login_at TEXT
        );
        """
    )
    ph = bcrypt.hash(password)
    cur.execute(
        "INSERT OR IGNORE INTO users(username, password_hash, is_admin, created_at) VALUES (?,?,?,?)",
        (username, ph, 1 if is_admin else 0, datetime.utcnow().isoformat()),
    )
    conn.commit(); conn.close()


def verify_login(username: str, password: str) -> bool:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close(); return False
    ok = bcrypt.verify(password, row["password_hash"])
    if ok:
        cur.execute("UPDATE users SET last_login_at=? WHERE id=?", (datetime.utcnow().isoformat(), row["id"]))
        conn.commit()
    conn.close()
    return ok

