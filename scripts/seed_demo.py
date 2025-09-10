from core.db import get_conn, init_db, rebuild_fts

init_db()
conn = get_conn(); cur = conn.cursor()

data = [
    ("vlanCktEp", "VLAN Circuit EPG", "fv", "EPG ve bulunduğu AP ilişkisini VLAN bağlamında tutar.", [
        ("epgDn", "EPG distinguished name"),
        ("encap", "Dot1q encapsulation (vlan-<id>)"),
    ]),
    ("l3extOut", "L3Out", "l3ext", "Dış yönlendirme politikası; nameAlias ile mapping yapılabilir.", [
        ("name", "Primary name"),
        ("nameAlias", "Alias; regex aramaya uygun"),
    ]),
    ("bgpPeerEntry", "BGP Peer Entry", "bgp", "BGP komşu oper durumu, flap zamanı, dn içerir.", [
        ("dn", "Distinguished name; interface ve tenant bağlamı"),
        ("operSt", "Operational state"),
        ("lastFlapTs", "Last flap timestamp"),
    ]),
]

for name, label, category, descr, props in data:
    cur.execute("INSERT OR IGNORE INTO classes(module, name, label, category, descr) VALUES (?,?,?,?,?)",
                (category, name, label, category, descr))
    cur.execute("SELECT id FROM classes WHERE name=?", (name,))
    cid = cur.fetchone()[0]
    for pname, pdesc in props:
        cur.execute("INSERT INTO props(class_id,name,descr) VALUES(?, ?, ?)", (cid, pname, pdesc))

conn.commit(); conn.close()
rebuild_fts()
print("Demo veriler yüklendi ve FTS güncellendi.")