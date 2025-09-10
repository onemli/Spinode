from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Static, TextArea

class DiagramScreen(Screen):
    BINDINGS = [("q", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="title")
        yield Static("", id="body")   # ← BU YOKTU, EKLEDİK
        yield Footer()

    def on_show(self) -> None:
        title = getattr(self.app, "diagram_title", "Diagram")
        content = getattr(self.app, "diagram_content", "")
        self.query_one("#title", Static).update(title)
        self.query_one("#body", Static).update(content)

    def on_resume(self) -> None:
        data = self.get_data() or {}
        self.query_one("#title", Static).update(data.get("title") or "Diagram")
        self.query_one("#area", TextArea).load_text(data.get("content") or "")
