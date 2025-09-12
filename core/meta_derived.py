# core/meta_derived.py
from typing import List, Dict, Any
from core.db import get_conn

def get_prop_info(class_name: str) -> List[Dict[str, Any]]:
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT p.name, p.is_naming, p.ptype, p.regex
        FROM props p
        JOIN classes c ON c.id = p.class_id
        WHERE c.name = ?
        ORDER BY p.is_naming DESC, p.name
    """, (class_name,))
    props = [dict(name=r[0], is_naming=bool(r[1]), ptype=r[2], regex=r[3]) for r in cur.fetchall()]

    # enums
    enums_map: Dict[str, List[Dict[str,str]]] = {}
    cur.execute("""
        SELECT p.prop_name, p.const_name, p.const_label, p.const_value
        FROM prop_enums p
        JOIN classes c ON c.id = p.class_id
        WHERE c.name = ?
    """, (class_name,))
    for prop_name, cname, clabel, cval in cur.fetchall():
        enums_map.setdefault(prop_name, []).append({"name": cname, "label": clabel, "value": cval})

    for pr in props:
        pr["enums"] = enums_map.get(pr["name"], [])
    conn.close()
    return props

def derive_pipeline_options(class_name: str) -> List[Dict[str, str]]:
    """Sınıfa göre otomatik pipeline (grep/sort/uniq) seçenekleri."""
    props = get_prop_info(class_name)
    names = {p["name"] for p in props}
    out: List[Dict[str,str]] = []

    # dn varsa dn için grep
    if "dn" in names:
        out.append({"id": "grep:^dn", "label": 'grep "^dn"'})
    # name/nameAlias varsa
    if "name" in names or "nameAlias" in names:
        out.append({"id": "grep:^name", "label": 'grep "^name "'})
    if "epgDn" in names:
        out.append({"id": "grep:^epgDn", "label": 'grep "^epgDn"'})
    # BGP benzeri
    if "operSt" in names or "lastFlapTs" in names:
        out.append({"id": "grep:bgp", "label": 'grep "operSt\\|lastFlapTs"'})
    if "dn" in names and ("operSt" in names or "lastFlapTs" in names):
        out.append({"id": "grep:dn|operSt|lastFlapTs", "label": 'grep "dn\\|operSt\\|lastFlapTs"'})
    # default sort/uniq
    out.append({"id": "sortu", "label": "sort -u"})
    out.append({"id": "uniq", "label": "uniq"})
    return out

def derive_templates(class_name: str) -> List[Dict[str, Any]]:
    """Heuristik: isim, alias, descr, enum'lu prop'lar, encap gibi alanlara göre öneriler."""
    props = get_prop_info(class_name)
    names = {p["name"] for p in props}
    t: List[Dict[str, Any]] = []

    # Alias regex
    if "nameAlias" in names:
        t.append({
            "title": "Alias regex (ID listesi)",
            "conds": [{"prop": "nameAlias", "op": "regex", "value": "(123|456|789)"}],
            "pipes": ["grep:^name", "sortu"]
        })
    # Name startswith
    if "name" in names:
        t.append({
            "title": "Name prefix",
            "conds": [{"prop": "name", "op": "startswith", "value": "OUT-"}],
            "pipes": ["grep:^name"]
        })
    # Description contains
    if "descr" in names:
        t.append({
            "title": "Description contains",
            "conds": [{"prop": "descr", "op": "contains", "value": "DMZ"}],
            "pipes": []
        })
    # Enums: ilk enum'lu prop için IN örneği
    for p in props:
        if p["enums"]:
            sample = ",".join([e["name"] for e in p["enums"][:3]]) or ""
            if sample:
                t.append({
                    "title": f"{p['name']} in (enum)",
                    "conds": [{"prop": p["name"], "op": "in", "value": sample}],
                    "pipes": []
                })
            break
    # VLAN encap benzeri
    for candidate in ("encap", "vlan", "encapId"):
        if candidate in names:
            t.append({
                "title": "VLAN encap contains",
                "conds": [{"prop": candidate, "op": "contains", "value": "vlan-905"}],
                "pipes": []
            })
            break

    return t
