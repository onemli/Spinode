from datetime import datetime
from core.db import get_conn

def init_audit():
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS query_runs(
            id INTEGER PRIMARY KEY,
            username TEXT,
            class_name TEXT,
            moquery_text TEXT,
            status TEXT,
            error_text TEXT,
            ran_at TEXT
        );
        """
    )
    conn.commit(); conn.close()


def log_query_run(username: str, class_name: str, moquery_text: str, status: str = "draft", error_text: str | None = None):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO query_runs(username, class_name, moquery_text, status, error_text, ran_at) VALUES (?,?,?,?,?,?)",
        (username, class_name, moquery_text, status, error_text, datetime.utcnow().isoformat()),
    )
    conn.commit(); conn.close()
# ADD at bottom (or appropriate place)
from typing import List, Dict, Any
from core.db import get_conn

def get_recent_logs(limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT user, class_name, command, status, created_at
        FROM logs
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(user=r["user"], class_name=r["class_name"], command=r["command"],
                 status=r["status"], created_at=r["created_at"]) for r in rows]
