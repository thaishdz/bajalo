from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.validation import Function
from textual.widgets import Footer, Header, Input, Label, Select

from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FOLDERS, FORMATS
from bajalo.utils import is_valid_url


class BajaloApp(App):
    TITLE = "bajalo"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(
            placeholder="Paste the video URL",
            id="url",
            validators=[
                Function(
                    is_valid_url, "Enter a full URL starting with http:// or https://"
                ),
            ],
        )
        yield Label("", id="url_error")
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

    @on(Input.Changed, "#url")
    def show_url_error(self, event):
        errors = event.validation_result.failure_descriptions
        self.query_one("#url_error", Label).update("\n".join(errors))

    @on(Select.Changed, "#media_type")
    def toggle_option_groups(self, event):
        is_video = event.value == "video"
        self.query_one("#video_options").display = is_video
        self.query_one("#audio_options").display = not is_video


def main():
    BajaloApp().run()
