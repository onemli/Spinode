from typing import List
from core.db import get_conn

def neighbors_of(class_name: str) -> List[str]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(c2.name, r.dst_name) AS dst
        FROM relations r
        LEFT JOIN classes c1 ON c1.id = r.src_class_id
        LEFT JOIN classes c2 ON c2.id = r.dst_class_id
        WHERE c1.name = ?
        ORDER BY dst
        """,
        (class_name,)
    )
    nbs = [row[0] for row in cur.fetchall() if row[0]]
    conn.close()
    return nbs

def to_mermaid(root: str) -> str:
    nbs = neighbors_of(root)
    lines = ["graph TD"]
    if not nbs:
        return "".join(lines + [f"  {root}"])
    for nb in nbs:
        lines.append(f"  {root} --> {nb}")
    return "".join(lines)

def to_ascii(root: str) -> str:
    nbs = neighbors_of(root)
    if not nbs:
        return f"+-----------+| {root:<9} |+-----------+"
    lines = [f"[{root}]"]
    for nb in nbs[:12]:  # ekranda taşıma yapmasın
        lines.append(f"  └─> [{nb}]")
    if len(nbs) > 12:
        lines.append("  └─> [...]")
    return "".join(lines)