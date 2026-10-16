from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.validation import Function
from textual.widgets import Button, Footer, Header, Input, Label, ProgressBar, Select
from yt_dlp.utils import DownloadError, remove_terminal_sequences

from bajalo.downloader import download_audio, download_video
from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FOLDERS, FORMATS
from bajalo.theme import TERMINAL_THEME
from bajalo.utils import is_valid_url


def field(label, widget):
    """A widget with a small caption above it."""
    return Vertical(Label(label), widget, classes="field")


class BajaloApp(App):
    TITLE = "bajalo"
    CSS_PATH = "tui.tcss"

    def on_mount(self):
        self.register_theme(TERMINAL_THEME)
        self.theme = "terminal"

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="form"):
            with Vertical(classes="group") as group:
                group.border_title = "Video URL"
                yield Input(
                    placeholder="Paste the video URL",
                    id="url",
                    validators=[
                        Function(
                            is_valid_url,
                            "Enter a full URL starting with http:// or https://",
                        ),
                    ],
                )
                yield Label("", id="url_error")
            with Horizontal(classes="group row") as group:
                group.border_title = "Output"
                yield field(
                    "Type",
                    Select(
                        [("video", "video"), ("only audio", "audio")],
                        id="media_type",
                        allow_blank=False,
                        value="video",
                    ),
                )
                yield field(
                    "Save to",
                    Select.from_values(
                        FOLDERS, id="folder", allow_blank=False, value="Desktop"
                    ),
                )
            with Horizontal(id="video_options", classes="group row") as group:
                group.border_title = "Video options"
                yield field(
                    "Quality",
                    Select(
                        FORMATS.items(),
                        id="quality",
                        allow_blank=False,
                        value=FORMATS["1080p"],
                    ),
                )
                yield field(
                    "Format",
                    Select(
                        EXTENSIONS.items(),
                        id="extension",
                        allow_blank=False,
                        value=EXTENSIONS["mp4"],
                    ),
                )
            with Vertical(id="audio_options", classes="group") as group:
                group.border_title = "Audio options"
                yield field(
                    "Format",
                    Select(
                        AUDIO_FORMATS.items(),
                        id="audio_format",
                        allow_blank=False,
                        value=AUDIO_FORMATS["mp3"],
                    ),
                )
            yield Button("Download", id="download", variant="primary")
            with Vertical(id="progress_box", classes="group") as group:
                group.border_title = "Downloading..."
                yield ProgressBar(id="progress", show_eta=False)
                yield Label("", id="download_error", markup=False)
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
        self.query_one("#download", Button).disabled = True
        self.query_one("#progress_box").display = True
        self.query_one("#progress_box").border_title = "Downloading..."
        self.query_one("#progress_box").remove_class("failed")
        self.query_one("#progress", ProgressBar).update(total=None, progress=0)
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
        try:
            download(*args, progress_hook=self.update_progress, quiet=True)
            self.call_from_thread(self.notify, "Download finished!")
            self.call_from_thread(self.set_progress_title, "Done")
        except DownloadError as error:
            self.call_from_thread(
                self.show_download_error, remove_terminal_sequences(error.msg)
            )
        finally:
            self.call_from_thread(self.enable_download_button)

    def enable_download_button(self):
        self.query_one("#download", Button).disabled = False

    def update_progress(self, progress):  # yt-dlp calls this on every progress update
        total_bytes = progress.get("total_bytes") or progress.get(
            "total_bytes_estimate"
        )
        downloaded_bytes = progress.get("downloaded_bytes") or 0
        # "finished" only means this file is downloaded: a video fetches two files
        # and ffmpeg still has to merge them, so the real end is in run_download.
        if progress.get("status") == "finished":
            self.call_from_thread(self.set_progress_title, "Processing...")
        else:
            self.call_from_thread(self.set_progress_title, "Downloading...")
        self.call_from_thread(
            self.query_one("#progress", ProgressBar).update,
            total=total_bytes,
            progress=downloaded_bytes,
        )

    def set_progress_title(self, title):
        self.query_one("#progress_box").border_title = title

    def show_download_error(self, message):
        self.query_one("#download_error", Label).update(message)
        self.query_one("#progress_box").add_class("failed")
        self.set_progress_title("Failed")


def main():
    BajaloApp().run()
