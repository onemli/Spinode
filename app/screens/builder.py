# app/screens/builder.py
import re
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Static, Input, Select, Button, TextArea, Checkbox, ListView, ListItem  # templates için
from core.meta_derived import derive_pipeline_options, derive_templates, get_prop_info
from textual.containers import Vertical, Horizontal
from core.db import get_conn
from core.moquery import Condition, render_moquery
from core.diagram import to_mermaid, to_ascii
from core.audit import log_query_run

OPS = [
    ("= (exact)", "exact"),
    ("contains", "contains"),
    ("regex", "regex"),
    ("starts with", "startswith"),
    ("in list", "in"),
    ("!= (not equal)", "ne"),
    ("> (greater than)", "gt"),
    (">= (greater or equal)", "ge"),
    ("< (less than)", "lt"),
    ("<= (less or equal)", "le"),
]

class BuilderScreen(Screen):
    """SPINODE — Builder"""
    BINDINGS = [
        ("enter", "add_cond", "Koşul ekle"),
        ("s", "save", "Kaydet/Log"),
        ("c", "copy", "Kopyala"),
        ("d", "diagram", "Diagram"),
        ("q", "app.pop_screen", "Back"),
    ]

    CSS = """
    #split { height: 1fr; }
    #left, #right { padding: 1; }
    #left  { width: 46%; border: round $primary; }
    #right { width: 1fr;  border: round $secondary; }
    #props, #templates, #examples { margin-top: 1; height: 1fr; }
    #conds, #mq { border: round $secondary; background: $panel; }
    #pipeline { margin-top: 1; }
    #buttons { content-align: right middle; }
    #class_title { margin-bottom: 1; }
    """

    # ---- lifecycle
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="split"):
            # LEFT: CLASS & PROPS
            with Vertical(id="left"):
                yield Static("", id="class_title")
                with Horizontal():
                    yield Select([], prompt="Prop", id="prop")
                    yield Select(OPS, prompt="Op", id="op")
                yield Input(placeholder="value / regex / a,b,c", id="val")
                with Horizontal():
                    yield Button("+ Add", id="add")
                    yield Button("Clear", id="clear")

                yield Static("Props:", id="props_title")
                yield TextArea("", id="props", read_only=True)

                yield Static("Templates:", id="templates_title")
                yield ListView(id="templates")

                yield Static("Examples:", id="examples_title")
                yield TextArea("— örnekleri sonra dolduracağız —", id="examples", read_only=True)

            # RIGHT: CONDITIONS & PREVIEW
            with Vertical(id="right"):
                yield Static("Add Condition / Current:", id="conds_title")
                yield TextArea("(koşul yok)", id="conds", read_only=True)

                yield Static("Post-Processing (Pipeline):", id="pipeline_title")
                with Vertical(id="pipeline"):
                    with Vertical(id="pipeline"):
                        pass

                yield Static("Preview (final command):", id="mq_title")
                yield TextArea("", id="mq", read_only=True)

                with Horizontal(id="buttons"):
                    yield Button("Mermaid", id="mm")
                    yield Button("ASCII", id="ascii")
                    yield Button("Kaydet/Log", id="save")
        yield Footer()

    def on_show(self) -> None:
        """Her girişte — state sıfırla, seçili class'a göre prop'ları doldur."""
        self.conds: list[Condition] = []

        cls = getattr(self.app, "selected_class", None)
        if not cls:
            self.app.notify("Önce bir sınıf seçin (Home).", severity="warning")
            self.app.pop_screen()
            return
        self.cls = cls or "-"
        self.query_one("#class_title", Static).update(f"[b]Class: {self.cls}[/b]")

        # props doldur
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT p.name, p.is_naming FROM props p
            JOIN classes c ON c.id = p.class_id
            WHERE c.name = ?
            ORDER BY p.is_naming DESC, p.name
        """, (self.cls,))
        props = cur.fetchall()
        conn.close()
        if not props:
            props = [("name",1),("nameAlias",0),("dn",0),("epgDn",0)]

        self.query_one("#prop", Select).set_options([(p[0], p[0]) for p in props])
        self.query_one("#props", TextArea).load_text(
            "\n".join([f"• {p[0]}{' (naming)' if p[1] else ''}" for p in props])
        )


        # props listesi (dinamik)
        prop_rows = get_prop_info(self.cls)
        if not prop_rows:
            prop_rows = [{"name":"name","is_naming":1},{"name":"nameAlias","is_naming":0},{"name":"dn","is_naming":0}]
        self.query_one("#prop", Select).set_options([(p["name"], p["name"]) for p in prop_rows])
        self.query_one("#props", TextArea).load_text(
            "\n".join([f"• {p['name']}{' (naming)' if p.get('is_naming') else ''}" for p in prop_rows])
        )

        # # PIPELINE — dinamik
        # pipeline = self.query_one("#pipeline")
        # pipeline.remove_children()
        # self._pipe_ids = []  # seçili id'leri okumak için
        # for opt in derive_pipeline_options(self.cls):
        #     cb = Checkbox(opt["label"], id=f"pipe:{opt['id']}")
        #     pipeline.mount(cb)
        #     self._pipe_ids.append(f"pipe:{opt['id']}")
        pipeline = self.query_one("#pipeline")
        pipeline.remove_children()
        # widget_id -> logical_id haritası (Textual id'leri güvenli hale getiriyoruz)
        self._pipe_map: dict[str, str] = {}
        def _safe_id(logical_id: str) -> str:
            # yalnızca [A-Za-z0-9_-] izinli; diğerlerini '_' yap
            return "pipe_" + re.sub(r"[^A-Za-z0-9_-]", "_", logical_id)
        for opt in derive_pipeline_options(self.cls):
            logical_id = opt["id"]          # örn: grep:^dn, sortu, uniq
            wid = _safe_id(logical_id)      # örn: pipe_grep__dn, pipe_sortu
            cb = Checkbox(opt["label"], id=wid)
            pipeline.mount(cb)
            self._pipe_map[wid] = logical_id
        # TEMPLATES — dinamik
        tlist = self.query_one("#templates", ListView)
        tlist.clear()
        self._templates = derive_templates(self.cls)
        for i, tpl in enumerate(self._templates):
            tlist.append(ListItem(Static(f"• {tpl['title']}"), id=f"tpl_{i}"))


        # temizle & önizleme
        self.query_one("#val", Input).value = ""
        self._refresh_preview()
        self.query_one("#prop", Select).focus()
    # ---- actions
    def action_add_cond(self):
        self._add_condition()

    def action_save(self):
        mq = self.query_one("#mq", TextArea).text
        user = getattr(self.app, "user", "unknown")
        log_query_run(user, self.cls, mq, status="draft", error_text=None)
        self.app.notify("Kaydedildi / Loglandı", severity="information")

    def action_copy(self):
        text = self.query_one("#mq", TextArea).text
        try:
            # Textual >=0.48
            self.app.copy_to_clipboard(text)
            self.app.notify("Komut kopyalandı", severity="information")
        except Exception:
            self.app.notify("Kopyalama desteklenmiyor", severity="warning")

    def action_diagram(self):
        mer = to_mermaid(self.cls)
        self.app.diagram_title = f"Mermaid for {self.cls}"
        self.app.diagram_content = mer
        self.app.push_screen("diagram")
    # ---- events
    def on_button_pressed(self, ev: Button.Pressed) -> None:
        if ev.button.id == "add":
            self._add_condition()
        elif ev.button.id == "clear":
            self.conds = []
            self._refresh_preview()
        elif ev.button.id == "mm":
            self.action_diagram()
        elif ev.button.id == "ascii":
            asc = to_ascii(self.cls)
            self.app.diagram_title = f"ASCII for {self.cls}"
            self.app.diagram_content = f"```\n{asc}\n```"
            self.app.push_screen("diagram")
        elif ev.button.id == "save":
            self.action_save()

    def on_checkbox_changed(self, _: Checkbox.Changed) -> None:
        self._refresh_preview()

    # ---- helpers
    def _add_condition(self):
        prop = self.query_one("#prop", Select).value
        op = self.query_one("#op", Select).value
        val = self.query_one("#val", Input).value
        if not prop or not op or not val:
            self.app.notify("Prop/Op seç ve Value gir", severity="warning"); return
        self.conds.append(Condition(prop=prop, op=op, value=val))
        self.query_one("#val", Input).value = ""
        self._refresh_preview()

    def _refresh_preview(self):
        # pipeline topla (dinamik id eşlemesi ile)
        greps = []
        sortu = False
        uniq = False
        for wid, logical in getattr(self, "_pipe_map", {}).items():
            cb = self.query_one(f"#{wid}", Checkbox)
            if not cb.value:
                continue
            if logical == "grep:^dn":
                greps.append('^dn')
            elif logical == "grep:^name":
                greps.append('^name ')
            elif logical == "grep:^epgDn":
                greps.append('^epgDn')
            elif logical == "grep:bgp":
                greps.append('operSt\\|lastFlapTs')
            elif logical == "grep:dn|operSt|lastFlapTs":
                greps.append('dn\\|operSt\\|lastFlapTs')
            elif logical == "sortu":
                sortu = True
            elif logical == "uniq":
                uniq = True

        greps_cli = [f'"{g}"' for g in greps] if greps else None
        mq = render_moquery(self.cls, self.conds, greps=greps_cli, sort_unique=sortu, uniq=uniq)
        lines = [f"{c.prop} {c.op} {c.value}" for c in self.conds] or ["(koşul yok)"]
        self.query_one("#conds", TextArea).load_text("\n".join(lines))
        self.query_one("#mq", TextArea).load_text(mq)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not str(event.list_view.id) == "templates":
            return
        item_id = event.item.id or ""
        if not item_id.startswith("tpl_"):
            return
        idx = int(item_id.split("_")[1])
        tpl = self._templates[idx]
        # koşulları uygula
        self.conds = [Condition(prop=c["prop"], op=c["op"], value=c["value"]) for c in tpl.get("conds", [])]
        # tüm pipeline checkbox'larını temizle
        for wid in list(getattr(self, "_pipe_map", {}).keys()):
            self.query_one(f"#{wid}", Checkbox).value = False
        # istenenleri işaretle
        for logical in tpl.get("pipes", []):
            target = next((wid for wid, lid in self._pipe_map.items() if lid == logical), None)
            if target:
                self.query_one(f"#{target}", Checkbox).value = True
        self._refresh_preview()
