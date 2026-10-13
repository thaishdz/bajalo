from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, Select

from bajalo.options import FOLDERS


class BajaloApp(App):
    TITLE = "bajalo"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Paste the video URL", id="url")
        yield Select(
            [("video", "video"), ("only audio", "audio")],
            id="media_type",
            allow_blank=False,
            value="video",
        )
        yield Select.from_values(
            FOLDERS, id="folder", allow_blank=False, value="Desktop"
        )
        yield Footer()


def main():
    BajaloApp().run()
