from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Vertical
from core.auth import verify_login
from core.audit import init_audit


class LoginScreen(Screen):
    """Basit ve ortalanmış giriş ekranı."""

    CSS = """
    Screen { align: center middle; }
    #box { width: 60; padding: 1; border: round $primary; align: center middle; }
    #title { content-align: center middle; margin-bottom: 1; }
    """

    BINDINGS = [("escape", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("🔐  Giriş yap", id="title"),
            Input(placeholder="Kullanıcı adı", id="username"),
            Input(placeholder="Şifre", password=True, id="password"),
            Button("Giriş", id="login"),
            Static("", id="msg"),
            id="box",
        )

    def on_mount(self) -> None:
        self.query_one("#username", Input).focus()
        init_audit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login":
            self.do_login()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("username", "password"):
            self.do_login()

    def do_login(self) -> None:
        u = self.query_one("#username", Input).value.strip()
        p = self.query_one("#password", Input).value
        ok = verify_login(u, p)
        if ok:
            self.app.user = u
            self.app.push_screen("home")
        else:
            self.query_one("#msg", Static).update("[red]Hatalı kullanıcı adı/şifre[/red]")

