from textual.app import App
from app.screens.login import LoginScreen
from app.screens.home import HomeScreen
from app.screens.builder import BuilderScreen
from app.screens.diagram import DiagramScreen

class SpinodeApp(App):
    CSS = """
    Screen { background: $background; color: $foreground; }
    """
    user: str | None = None
    selected_class: str | None = None

    def on_mount(self) -> None:
        self.install_screen(LoginScreen(), name="login")
        self.install_screen(HomeScreen(), name="home")
        self.install_screen(BuilderScreen(), name="builder")
        self.install_screen(DiagramScreen(), name="diagram")
        self.push_screen("login")

if __name__ == "__main__":
    SpinodeApp().run()