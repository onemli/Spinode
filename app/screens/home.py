# REPLACE HomeScreen class (tamamı)
from core.audit import get_recent_logs
from rich.table import Table  # ADD
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Static, Input, DataTable, Button, TextArea

from textual.containers import Vertical, Horizontal
from core.search import fts_query
from core.db import get_conn

class HomeScreen(Screen):
    BINDINGS = [("q", "app.pop_screen", "Back"), ("x", "logout", "Quit")]

    CSS = """
    #hdrline { padding: 0 1; color: $primary; }
    #filters { padding: 0 1; color: $secondary; }
    #split { height: 1fr; }
    #left  { width: 46%; border: round $primary; margin: 1; }
    #right { width: 1fr;  border: round $secondary; margin: 1; }
    #search { margin: 1 1 0 1; }
    #table  { margin: 1; height: 1fr; }
    #details { margin: 1; }
    #actions { margin: 0 1 1 1; content-align: right middle; }
    .hint { color: $secondary; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="hdrline")
        yield Input(placeholder="fv, vlan, bgp… (isim, açıklama, prop içinde arar)", id="search")
        yield Static("Filters: [Namespace: *] [Has Regex: ✓]", id="filters")
        with Horizontal(id="split"):
            # LEFT: classes table
            with Vertical(id="left"):
                yield Static("CLASSES (FTS) —  [↑↓] hareket, [Enter] seç", classes="hint")
                t = DataTable(id="table")
                t.add_columns("Class", "Label", "Category", "Descr")
                t.cursor_type = "row"
                t.show_cursor = True
                yield t
            # RIGHT: details
            with Vertical(id="right"):
                yield Static("CLASS DETAILS", classes="hint")
                yield Static("", id="details")
        with Horizontal(id="actions"):
            yield Static("Recent Logs", classes="logs_title")
            yield Static("", id="logs")  # Rich Table render edilecek
        yield Footer()

    def on_show(self) -> None:
        self.query_one("#hdrline", Static).update(f"👤 User: {getattr(self.app, 'user', '?')}")
        # temiz başlangıç
        self.query_one("#search", Input).value = ""
        t: DataTable = self.query_one("#table", DataTable)
        t.clear()
        self.query_one("#details", Static).update("")
        self.query_one("#search", Input).focus()
        # LOG TABLE (Rich)
        logs_static: Static = self.query_one("#logs", Static)
        table = Table(show_lines=False)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("User", style="magenta", no_wrap=True)
        table.add_column("Class", style="yellow", no_wrap=True)
        table.add_column("Command", overflow="fold")
        table.add_column("Status", style="green", no_wrap=True)
        for row in get_recent_logs(limit=30):
            table.add_row(row["created_at"], row["user"], row["class_name"], row["command"], row["status"])
        logs_static.update(table)


    def action_logout(self) -> None:
        self.app.user = None
        self.app.pop_screen()


    def on_input_changed(self, ev: Input.Changed) -> None:
        items = fts_query(ev.value, limit=200)
        t: DataTable = self.query_one("#table", DataTable)
        t.clear()
        row_keys = []
        for r in items:
            descr = (r.get("descr") or "").replace("\n"," ")
            if len(descr) > 100: descr = descr[:100] + "…"
            rk = t.add_row(r["name"], r.get("label") or "", r.get("category") or "", descr)
            row_keys.append(rk)
        if row_keys:
            try:
                t.move_cursor(row=0, column=0)
            except Exception:
                pass
            # ilk satırın detayını da göster
            self._update_details_by_rowkey(row_keys[0])

    # ok tuşları/Enter ile gezinme & seçim
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_details_by_rowkey(event.row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # Enter'a basıldığında seçili satır üzerinden builder'a
        self._goto_builder_with_rowkey(event.row_key)

    def on_button_pressed(self, ev: Button.Pressed) -> None:
        if ev.button.id == "to_builder":
            # butonla geçişte mevcut cursor_row baz alınır
            t: DataTable = self.query_one("#table", DataTable)
            if not t.has_focus:
                t.focus()
            key = t.cursor_row
            if key is None and t.row_count:
                key = t.get_row_at(0).key
            self._goto_builder_with_rowkey(key)
        elif ev.button.id == "logout":
            self.app.user = None
            self.app.pop_screen()

    # helpers
    def _update_details_by_rowkey(self, row_key) -> None:
        if row_key is None: 
            return
        t: DataTable = self.query_one("#table", DataTable)
        try:
            row = t.get_row(row_key)
        except Exception:
            return
        cls_name, label, category, descr = row[0], row[1], row[2], row[3]
        # DB'den rn/naming props/quick props & relations çek
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT rn_format, naming_props_csv, descr FROM classes WHERE name=?", (cls_name,))
        cinfo = cur.fetchone()
        cur.execute("""
            SELECT p.name, p.is_naming
            FROM props AS p
            JOIN classes AS c ON c.id = p.class_id
            WHERE c.name = ?
            ORDER BY p.is_naming DESC, p.name
            LIMIT 12
        """, (cls_name,))
        props = cur.fetchall()
        cur.execute("""
            SELECT COALESCE(c2.name, r.dst_name) AS dst
            FROM relations r
            LEFT JOIN classes c1 ON c1.id = r.src_class_id
            LEFT JOIN classes c2 ON c2.id = r.dst_class_id
            WHERE c1.name = ?
            ORDER BY dst LIMIT 10
        """, (cls_name,))
        rels = [r[0] for r in cur.fetchall()]
        conn.close()

        rn = cinfo["rn_format"] if cinfo and cinfo["rn_format"] else "-"
        nprops = cinfo["naming_props_csv"] if cinfo and cinfo["naming_props_csv"] else "-"
        descr_full = cinfo["descr"] if cinfo and cinfo["descr"] else descr

        props_lines = "  • " + "\n  • ".join([f"{p[0]}{' (naming)' if p[1] else ''}" for p in props]) if props else "  • -"
        rels_lines = ""
        if rels:
            # mini ascii
            rels_lines = f"  {cls_name} ─┬─> " + "\n  ".join([f"      └─> {r}" for r in rels])

        detail = (
f"""Name: {cls_name}
Label: {label}
Category: {category}
rnFormat: {rn}
namingProps: {nprops}

Description:
  {descr_full or '-'}

Props (quick pick):
{props_lines}

Relations (mini graph):
{rels_lines or '  • -'}

Quick Actions:
[B] Open Builder   [D] Diagram   [E] Examples"""
        )
        self.query_one("#details", Static).update(detail)
    # Satır vurgusu değiştiğinde (ok tuşlarıyla gezerken genelde bu tetiklenir)
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_details_by_rowkey(event.row_key)

    # Hücre vurgusu değiştiğinde (bazı sürümlerde satır yerine hücre tetiklenir)
    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        t: DataTable = self.query_one("#table", DataTable)
        self._update_details_by_rowkey(t.cursor_row)


    def _goto_builder_with_rowkey(self, row_key) -> None:
        t: DataTable = self.query_one("#table", DataTable)
        if t.row_count == 0 or row_key is None:
            self.app.bell(); return
        try:
            row = t.get_row(row_key)
        except Exception:
            self.app.bell(); return
        self.app.selected_class = row[0]
        self.app.push_screen("builder")
