from dataclasses import dataclass
from typing import List, Literal
import re
import shlex

Op = Literal[
    "exact",
    "contains",
    "regex",
    "startswith",
    "in",
    "ne",
    "gt",
    "ge",
    "lt",
    "le",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
]

@dataclass
class Condition:
    prop: str
    op: Op
    value: str

def build_filter_string(class_name: str, conds: List[Condition]) -> str:
    pieces = []
    for c in conds:
        op = {"!=": "ne", ">": "gt", ">=": "ge", "<": "lt", "<=": "le"}.get(c.op, c.op)
        star = "*" if op in ("contains", "regex", "startswith", "in") else ""
        raw_val = c.value
        if op == "startswith":
            val = f"^{re.escape(raw_val)}"
        elif op == "contains":
            val = re.escape(raw_val)
        elif op == "in":
            items = [re.escape(x.strip()) for x in raw_val.split(",") if x.strip()]
            val = "(" + "|".join(items) + ")"
            star = "*"
        elif op == "regex":
            val = raw_val
        else:
            val = raw_val
        val = val.replace('"', '\\"')
        op_symbol = {
            "ne": "!",
            "gt": ">",
            "ge": ">=",
            "lt": "<",
            "le": "<=",
        }.get(op, "")
        pieces.append(f'{class_name}.{c.prop}{op_symbol}{star}"{val}"')
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
        cmd += f" -f {shlex.quote(fstr)}"
    if greps:
        for g in greps:
            cmd += f" | grep {shlex.quote(g)}"
    # sort -u uniq’u zaten kapsar; ikisi birden seçiliyse sort -u yeter
    if sort_unique:
        cmd += " | sort -u"
    elif uniq:
        cmd += " | uniq"
    return cmd


