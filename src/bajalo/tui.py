from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Select

from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FOLDERS, FORMATS


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
        with Vertical(id="video_options"):
            yield Select(
                FORMATS.items(), id="quality", allow_blank=False, value=FORMATS["1080p"]
            )
            yield Select(
                EXTENSIONS.items(),
                id="extension",
                allow_blank=False,
                value=EXTENSIONS["mp4"],
            )
        with Vertical(id="audio_options"):
            yield Select(
                AUDIO_FORMATS.items(),
                id="audio_format",
                allow_blank=False,
                value=AUDIO_FORMATS["mp3"],
            )
        yield Footer()

    @on(Select.Changed, "#media_type")
    def toggle_option_groups(self, event):
        is_video = event.value == "video"
        self.query_one("#video_options").display = is_video
        self.query_one("#audio_options").display = not is_video


def main():
    BajaloApp().run()
