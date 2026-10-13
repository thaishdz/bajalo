from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label


class BajaloApp(App):
    TITLE = "bajalo"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Hello from bajalo")
        yield Footer()


def main():
    BajaloApp().run()