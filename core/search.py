from typing import List, Dict
from core.db import get_conn

def fts_query(q: str, limit: int = 20) -> List[Dict]:
    q = q.strip()
    if not q:
        return []
    tokens = [t for t in q.split() if t]
    match = " ".join(f"{t}*" for t in tokens)
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.name, c.label, c.category, c.descr
        FROM class_fts f
        JOIN classes c ON c.id = f.rowid
        WHERE f.content MATCH ?
        LIMIT ?;
        """,
        (match, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
