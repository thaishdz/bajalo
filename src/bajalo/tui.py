from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.validation import Function
from textual.widgets import Button, Footer, Header, Input, Label, Select

from bajalo.downloader import download_audio, download_video
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
        yield Button("Download", id="download", variant="primary")
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

    @on(Button.Pressed, "#download")
    def start_download(self):
        url = self.query_one("#url", Input).value.strip()
        if not is_valid_url(url):
            self.notify("Enter a valid URL", severity="error")
            return
        media_type = self.query_one("#media_type", Select).value
        folder = str(Path.home() / self.query_one("#folder", Select).value)
        if media_type == "video":
            quality = self.query_one("#quality", Select).value
            extension = self.query_one("#extension", Select).value
            self.run_download(download_video, url, folder, quality, extension)
        else:
            audio_format = self.query_one("#audio_format", Select).value
            self.run_download(download_audio, url, folder, audio_format)

    @work(thread=True)
    def run_download(self, download, *args):
        download(*args, quiet=True)

    def media_type(self, media_type):
        
def main():
    BajaloApp().run()
