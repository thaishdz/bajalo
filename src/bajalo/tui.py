import json
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.validation import Function
from textual.widgets import Button, Footer, Header, Input, Label, ProgressBar, Select
from yt_dlp.utils import DownloadError, remove_terminal_sequences

from bajalo.downloader import download_audio, download_video
from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FOLDERS, FORMATS
from bajalo.theme import TERMINAL_THEME
from bajalo.utils import choose_folder_in_finder, is_existing_folder, is_valid_url


def field(label, widget):
    """A widget with a small caption above it."""
    return Vertical(Label(label), widget, classes="field")


class BajaloApp(App):
    TITLE = "bajalo"
    CSS_PATH = "tui.tcss"
    BINDINGS: ClassVar = [("escape", "quit", "Quit")]
    CONFIG_PATH = Path.home() / ".config" / "bajalo" / "config.json"
    download_path = None

    def on_mount(self):
        self.register_theme(TERMINAL_THEME)
        self.restore_settings()

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
            with Vertical(classes="group") as group:
                group.border_title = "Output"
                with Horizontal(classes="row"):
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
                        Select(
                            FOLDERS.items(),
                            id="folder",
                            allow_blank=False,
                            value=FOLDERS["Desktop"],
                        ),
                    )
                # Shown only when the custom folder is chosen in "Save to"
                with Vertical(id="custom_folder_box"):
                    yield Label("Enter a new folder destination:")
                    with Horizontal(id="custom_folder_row"):
                        yield Input(
                            placeholder="Folder path, e.g. ~/Movies",
                            id="custom_folder",
                            validators=[
                                Function(
                                    is_existing_folder, "Enter a folder that exists"
                                )
                            ],
                        )
                        # Finder's folder picker only exists on macOS
                        if sys.platform == "darwin":
                            yield Button("Browse...", id="browse")
                    yield Label("", id="custom_folder_error")
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
                yield Label("", id="download_path", markup=False)
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

    @on(Select.Changed, "#folder")
    def toggle_custom_folder(self, event):
        is_other = event.value == "other"
        self.query_one("#custom_folder_box").display = is_other

    @on(Button.Pressed, "#browse")
    def browse_folder(self):
        self.query_one("#browse", Button).disabled = True  # one Finder at a time
        self.pick_folder_in_finder()

    @work(thread=True)
    def pick_folder_in_finder(self):
        # osascript waits until a folder is chosen, so it runs off the UI thread
        try:
            folder = choose_folder_in_finder()
            if folder is not None:
                self.call_from_thread(self.set_custom_folder, folder)
        finally:
            self.call_from_thread(self.enable_browse_button)

    def set_custom_folder(self, folder):
        self.query_one("#custom_folder", Input).value = folder

    def enable_browse_button(self):
        self.query_one("#browse", Button).disabled = False

    @on(Input.Changed, "#custom_folder")
    def show_folder_error(self, event):
        errors = event.validation_result.failure_descriptions
        self.query_one("#custom_folder_error", Label).update("\n".join(errors))

    def selected_folder(self):
        choice = self.query_one("#folder", Select).value
        if choice != "other":
            return str(Path.home() / choice)  # ~/Desktop or ~/Downloads
        folder_path = self.query_one("#custom_folder", Input).value
        if not is_existing_folder(folder_path):
            return None
        return str(Path(folder_path.strip()).expanduser())

    @on(Button.Pressed, "#download")
    def start_download(self):
        url = self.query_one("#url", Input).value.strip()
        if not is_valid_url(url):
            self.notify("Enter a valid URL", severity="error")
            return

        folder_path = self.selected_folder()
        if folder_path is None:
            self.notify("Enter a folder that exists", severity="error")
            return
        self.write_config("folder", folder_path)

        self.query_one("#download", Button).disabled = True
        self.query_one("#progress_box").display = True
        self.query_one("#progress_box").border_title = "Downloading..."
        self.query_one("#progress_box").remove_class("failed", "done")
        self.query_one("#progress", ProgressBar).update(total=None, progress=0)

        media_type = self.query_one("#media_type", Select).value
        if media_type == "video":
            quality = self.query_one("#quality", Select).value
            extension = self.query_one("#extension", Select).value
            self.run_download(download_video, url, folder_path, quality, extension)
        else:
            audio_format = self.query_one("#audio_format", Select).value
            self.run_download(download_audio, url, folder_path, audio_format)

    @work(thread=True)
    def run_download(self, download, *args):
        try:
            path = download(*args, progress_hook=self.update_progress, quiet=True)
            self.call_from_thread(self.set_progress_title, "Completed")
            self.call_from_thread(self.show_download_path, path)
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

    def show_download_path(self, path):
        self.download_path = path
        label = self.query_one("#download_path", Label)
        # Only macOS can reveal the file, so only there it looks like a link
        is_link = sys.platform == "darwin"
        label.update(
            Text.assemble("Saved to: ", (path, "underline" if is_link else ""))
        )
        label.set_class(is_link, "link")
        self.query_one("#progress_box").add_class("done")

    @on(events.Click, "#download_path")
    def reveal_download(self):
        if sys.platform != "darwin":  # `open` doesn't exist elsewhere
            return
        # macOS: open Finder with the downloaded file selected
        subprocess.run(["open", "-R", self.download_path], check=False)

    def load_theme(self):
        config_dict = self.read_config()
        theme = config_dict.get("theme", "terminal")
        if theme in self.available_themes:
            return theme
        return "terminal"

    def load_folder(self):
        config_dict = self.read_config()
        folder = config_dict.get("folder", None)
        return folder

    def read_config(self):
        if not self.CONFIG_PATH.exists():
            return {}
        try:
            config = json.loads(self.CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            return {}
        return config

    def watch_theme(self, theme):
        self.write_config("theme", theme)

    def write_config(self, key, value):
        config = self.read_config()
        config[key] = value
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.CONFIG_PATH.write_text(json.dumps(config))

    def restore_settings(self):
        self.theme = self.load_theme()
        folder = self.load_folder()

        if folder is None:
            return
        for value in FOLDERS.values():
            path = str(Path.home() / value)
            if path == folder:
                self.query_one("#folder", Select).value = value
                return
        self.query_one("#folder", Select).value = "other"
        self.query_one("#custom_folder", Input).value = folder


def main():
    BajaloApp().run()
