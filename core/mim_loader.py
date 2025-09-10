import pkgutil, importlib, inspect, logging
from core.db import get_conn, init_db, rebuild_fts

try:
    import cobra.modelimpl as impl
except Exception as e:
    raise RuntimeError("Cobra SDK (cobra) kurulu mu? 'pip install cobra' ") from e

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def iter_modelimpl_modules():
    for mi in pkgutil.walk_packages(impl.__path__, impl.__name__ + "."):
        yield mi.name


def _prop_name(pmeta) -> str:
    # farklı cobra sürümleri: moPropName / propName / name
    return (
        getattr(pmeta, "moPropName", None)
        or getattr(pmeta, "propName", None)
        or getattr(pmeta, "name", None)
        or ""
    )


def _to_mo_name(obj) -> str:
    """Çocuk/ebeveyn/rs/rt objelerinden moClassName türet.
    obj bir sınıf objesi, meta, ya da 'cobra.model.fv.AEPg' string'i olabilir."""
    try:
        if hasattr(obj, "meta") and getattr(obj.meta, "moClassName", None):
            return obj.meta.moClassName
        if getattr(obj, "moClassName", None):
            return obj.moClassName
        if isinstance(obj, str):
            # 'cobra.model.fv.AEPg' gibi ise import etmeyi dene
            parts = obj.split(".")
            if len(parts) > 2:
                mod_name, cls_name = ".".join(parts[:-1]), parts[-1]
                try:
                    mod = importlib.import_module(mod_name)
                    cls = getattr(mod, cls_name, None)
                    if cls and hasattr(cls, "meta") and getattr(cls.meta, "moClassName", None):
                        return cls.meta.moClassName
                except Exception:
                    pass
            # değilse son parçayı döndür
            return parts[-1]
    except Exception:
        pass
    return str(obj)

def _iter_rel_names(collection):
    """Return iterable of destination class names without forcing class import."""
    # 1) Bazı sürümlerde isim listesi hazır gelir
    try:
        names = getattr(collection, "classNames", None)
        if names:
            for n in names:
                yield str(n)
            return
    except Exception:
        pass
def _iter_constants(pmeta):
    """PropMeta üzerindeki sabitleri (enum) yakala; sürümden bağımsız denemeler."""
    # cobra, _addConstant ile doldurur -> çoğunlukla pmeta._constants veya pmeta.constants görülür.
    for attr in ("constants", "_constants"):
        consts = getattr(pmeta, attr, None)
        if not consts:
            continue
        # dict benzeri mi?
        try:
            for name, info in consts.items():
                # bazı sürümlerde info tuple, bazılarında küçük obje
                label = None
                value = None
                if isinstance(info, (tuple, list)) and len(info) >= 2:
                    label, value = info[0], info[1]
                else:
                    label = getattr(info, "label", None) or getattr(info, "descr", None) or ""
                    value = getattr(info, "value", None)
                yield name, str(label) if label is not None else "", str(value) if value is not None else ""
        except Exception:
            # iterable dizi gibi olabilir
            try:
                for item in consts:
                    name = getattr(item, "name", None) or str(item)
                    label = getattr(item, "label", "") or ""
                    value = getattr(item, "value", "")
                    yield name, str(label), str(value)
            except Exception:
                pass
def _iter_props(meta):
    """Return iterable of (prop_name, pmeta) across cobra versions.
    Fallback to reflective scan when mapping-like methods are missing."""
    props = getattr(meta, "props", None) or {}
    # dict-like fast path
    try:
        return list(props.items())  # type: ignore[attr-defined]
    except Exception:
        pass
    out = []
    # some builds expose prop metas as attributes on `meta.props`
    for name in dir(props):
        if name.startswith("_"):
            continue
        try:
            pmeta = getattr(props, name)
            # crude check: a PropMeta usually has these attrs
            if hasattr(pmeta, "isNaming") or hasattr(pmeta, "category"):
                out.append((name, pmeta))
        except Exception:
            continue
    return out


def load_all():
    init_db()
    conn = get_conn(); cur = conn.cursor()

    # mevcut class isimleri
    cur.execute("SELECT name, id FROM classes;")
    existing = {r[0]: r[1] for r in cur.fetchall()}

    # 1) classes & props & relations(dst_name)
    for modname in iter_modelimpl_modules():
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            logging.warning("import fail %s: %s", modname, e)
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            meta = getattr(obj, "meta", None)
            if not meta or not getattr(meta, "moClassName", None):
                continue
            name = meta.moClassName
            if name in existing:
                cls_id = existing[name]
            else:
                naming_props = []
                for p in getattr(meta, "namingProps", []) or []:
                    pn = _prop_name(p)
                    if pn:
                        naming_props.append(pn)
                cur.execute(
                    """
                    INSERT INTO classes(module, name, label, category, rn_format, naming_props_csv, descr)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        modname,
                        name,
                        getattr(meta, "label", None),
                        str(getattr(meta, "category", "")),
                        getattr(meta, "rnFormat", None),
                        ",".join(naming_props) if naming_props else None,
                        getattr(meta, "descr", None),
                    ),
                )
                cls_id = cur.lastrowid
                existing[name] = cls_id

            # props — version-safe iteration
            for pname, pmeta in _iter_props(meta):
                descr = getattr(pmeta, "descr", None)
                is_naming = 1 if getattr(pmeta, "isNaming", False) else 0
                is_config = 1 if getattr(pmeta, "isConfig", False) else 0
                ptype = str(getattr(pmeta, "category", ""))  # PropCategory.* metni
                regex = getattr(pmeta, "regex", None)
                cur.execute(
                    """
                    INSERT INTO props(class_id, name, descr, is_naming, is_config, ptype, regex)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (cls_id, pname, descr, is_naming, is_config, ptype, regex),
                )
                # enum sabitlerini sakla
                for cname, clabel, cval in _iter_constants(pmeta):
                    cur.execute(
                        """
                        INSERT INTO prop_enums(class_id, prop_name, const_name, const_label, const_value)
                        VALUES (?,?,?,?,?)
                        """,
                        (cls_id, pname, cname, clabel, cval),)
                    
                # --- DEPLOYMENT PATHS (EKLE) ---
                for dpath in getattr(meta, "deploymentQueryPaths", []) or []:
                    try:
                        name = getattr(dpath, "name", None) or str(dpath)
                        descr = getattr(dpath, "descr", None) or ""
                        target = getattr(dpath, "targetClass", None)

                        # Hedef moClassName'ı çıkar
                        if target and hasattr(target, "meta") and getattr(target.meta, "moClassName", None):
                            target = target.meta.moClassName
                        elif isinstance(target, str):
                            # "cobra.model.nw.If" -> "If"
                            parts = target.split(".")
                            target = parts[-1] if parts else target

                        cur.execute(
                            """
                            INSERT INTO deployment_paths(class_id, name, descr, target_class)
                            VALUES (?,?,?,?)
                            """,
                            (cls_id, str(name), str(descr), str(target) if target else None),
                        )
                    except Exception:
                        continue
                # --- DEPLOYMENT PATHS SONU ---

            for rel_type, collection in (
                ("child", getattr(meta, "childClasses", []) or []),
                ("parent", getattr(meta, "parentClasses", []) or []),
                ("rs", getattr(meta, "targetRelations", []) or []),
                ("rt", getattr(meta, "sourceRelations", []) or []),
            ):
                for dst in _iter_rel_names(collection):
                    if not dst:
                        continue
                    cur.execute(
                        "INSERT INTO relations(src_class_id, rel_type, dst_name, descr) VALUES (?,?,?,?)",
                        (cls_id, rel_type, str(dst), None),
                    )

    conn.commit()

    # 2) ikinci geçiş: dst_name → dst_class_id
    cur.execute("SELECT id, dst_name FROM relations WHERE dst_class_id IS NULL AND dst_name IS NOT NULL;")
    for rel_id, dst_name in cur.fetchall():
        cur.execute("SELECT id FROM classes WHERE name=?", (dst_name,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE relations SET dst_class_id=? WHERE id=?", (row[0], rel_id))

    conn.commit(); conn.close()
    rebuild_fts()
    logging.info("MIM load ok — classes/props/relations doldu ve FTS güncellendi.")