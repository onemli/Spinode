# from textual.screen import Screen
# from textual.app import ComposeResult
# from textual.widgets import Input, Button, Static
# from textual.containers import Vertical
# from core.auth import verify_login
# from core.audit import init_audit

# class LoginScreen(Screen):
# # ADD inside LoginScreen class (top-level attribute)
#     CSS = """Screen { align: center middle; }
#     #box { width: 60; padding: 1; border: round $primary; }
#     # #title { content-align: center middle; margin-bottom: 1; }"""

#     BINDINGS = [("escape", "app.quit", "Quit")]

#     def compose(self) -> ComposeResult:
#         yield Vertical(
#             Static("🔐  Giriş yap", id="title"),
#             Input(placeholder="Kullanıcı adı", id="username"),
#             Input(placeholder="Şifre", password=True, id="password"),
#             Button("Giriş", id="login"),
#             Static("", id="msg"),
#             id="box",
#         )

#     def on_mount(self) -> None:
#         self.query_one("#username", Input).focus()
#         init_audit()

#     def on_button_pressed(self, event: Button.Pressed) -> None:
#         if event.button.id == "login":
#             self.do_login()

#     def on_input_submitted(self, event: Input.Submitted) -> None:
#         if event.input.id in ("username", "password"):
#             self.do_login()

#     def do_login(self):
#         u = self.query_one("#username", Input).value.strip()
#         p = self.query_one("#password", Input).value
#         ok = verify_login(u, p)
#         if ok:
#             self.app.user = u
#             self.app.push_screen("home")
#         else:
#             self.query_one("#msg", Static).update("[red]Hatalı kullanıcı adı/şifre[/red]")
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Static
from textual.containers import Vertical, Horizontal
from core.auth import verify_login
from core.audit import init_audit

class LoginScreen(Screen):
    CSS = """
    Screen { 
        align: center middle; 
    }
    #main-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #spacer-left, #spacer-right {
        width: 1fr;
        height: 100%;
    }
    #spacer-top, #spacer-bottom {
        width: 100%;
        height: 1fr;
    }
    #container {
        width: 80;
        height: auto;
        align: center middle;
    }
    #logo { 
        content-align: center middle; 
        margin-bottom: 2;
        color: $primary;
    }
    #box { 
        width: 60; 
        padding: 1; 
        border: round $primary;
        align: center middle;
    }
    #title { 
        content-align: center middle; 
        margin-bottom: 1; 
    }
    """

    BINDINGS = [("escape", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        logo_text = """
                                               

        """
        
        yield Vertical(
            Static("", id="spacer-top"),
            Horizontal(
                Static("", id="spacer-left"),
                Vertical(
                    Static(logo_text, id="logo"),
                    Vertical(
                        Input(placeholder="Kullanıcı adı", id="username"),
                        Input(placeholder="Şifre", password=True, id="password"),
                        Button("Giriş", id="login"),
                        Static("", id="msg"),
                        id="box",
                    ),
                    id="container"
                ),
                Static("", id="spacer-right"),
            ),
            Static("", id="spacer-bottom"),
            id="main-container"
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

    def do_login(self):
        u = self.query_one("#username", Input).value.strip()
        p = self.query_one("#password", Input).value
        ok = verify_login(u, p)
        if ok:
            self.app.user = u
            self.app.push_screen("home")
        else:
            self.query_one("#msg", Static).update("[red]Hatalı kullanıcı adı/şifre[/red]")
