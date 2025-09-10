from dataclasses import dataclass
from typing import List, Literal

Op = Literal["exact","contains","regex","startswith","in"]

@dataclass
class Condition:
    prop: str
    op: Op
    value: str

def build_filter_string(class_name: str, conds: List[Condition]) -> str:
    pieces = []
    for c in conds:
        star = "*" if c.op in ("contains", "regex", "startswith") else ""
        val = c.value
        if c.op == "startswith":
            val = f"^{val}"
        if c.op == "in":
            items = [x.strip() for x in val.split(",") if x.strip()]
            val = "(" + "|".join(items) + ")"
            star = "*"
        pieces.append(f'{class_name}.{c.prop}{star}"{val}"')
    return " ".join(pieces)

def render_moquery(
    class_name: str,
    conds: list[Condition],
    greps: list[str] | None = None,
    sort_unique: bool = False,
    uniq: bool = False,) -> str:
    fstr = build_filter_string(class_name, conds) if conds else ""
    cmd = f"moquery -c {class_name}"
    if fstr:
        cmd += f" -f '{fstr}'"
    if greps:
        for g in greps:
            cmd += f" | grep {g}"
    # sort -u uniq’u zaten kapsar; ikisi birden seçiliyse sort -u yeter
    if sort_unique:
        cmd += " | sort -u"
    elif uniq:
        cmd += " | uniq"
    return cmd


