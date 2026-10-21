import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import Label, ProgressBar
from yt_dlp.utils import DownloadError

from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FORMATS
from bajalo.tui import BajaloApp

URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
SAVED_TO = "/Users/me/Desktop/clip [abc].mp4"


@pytest.fixture(autouse=True)
def config_path(tmp_path, monkeypatch):
    """Keep the saved theme in a temp file so tests never touch the real config."""
    path = tmp_path / "bajalo" / "config.json"
    monkeypatch.setattr(BajaloApp, "CONFIG_PATH", path)
    return path


@pytest.fixture
def downloads():
    """Replace the real downloaders with fakes so no real download happens."""
    with (
        patch("bajalo.tui.download_video", return_value=SAVED_TO) as video,
        patch("bajalo.tui.download_audio", return_value=SAVED_TO) as audio,
    ):
        yield video, audio


def drive(scenario):
    """Run the app headless and hand it to `scenario(app, pilot)`."""

    async def run():
        app = BajaloApp()
        async with app.run_test(size=(100, 40)) as pilot:
            await scenario(app, pilot)

    asyncio.run(run())


async def download(app, pilot, url=URL):
    """Type a URL, press Download and wait for the worker to finish."""
    app.query_one("#url").value = url
    app.query_one("#download").press()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def box(app):
    return app.query_one("#progress_box")


def text(app, selector):
    return str(app.query_one(selector, Label).render())


# --- form -------------------------------------------------------------------


def test_starts_with_video_options_and_no_progress_box():
    async def scenario(app, pilot):
        assert app.query_one("#video_options").display
        assert not app.query_one("#audio_options").display
        assert not box(app).display

    drive(scenario)


def test_choosing_audio_swaps_the_option_groups():
    async def scenario(app, pilot):
        app.query_one("#media_type").value = "audio"
        await pilot.pause()
        assert not app.query_one("#video_options").display
        assert app.query_one("#audio_options").display

    drive(scenario)


def test_typing_an_invalid_url_shows_the_error_below_it():
    async def scenario(app, pilot):
        app.query_one("#url").value = "hola"
        await pilot.pause()
        assert "http://" in text(app, "#url_error")

    drive(scenario)


@pytest.mark.parametrize("url", ["", "hola", "ftp://example.com"])
def test_invalid_url_does_not_start_a_download(downloads, url):
    video, audio = downloads

    async def scenario(app, pilot):
        await download(app, pilot, url)
        assert not box(app).display
        assert not app.query_one("#download").disabled

    drive(scenario)
    video.assert_not_called()
    audio.assert_not_called()


# --- custom folder ----------------------------------------------------------


def test_custom_folder_input_shows_only_for_the_custom_choice():
    async def scenario(app, pilot):
        assert not app.query_one("#custom_folder_box").display
        app.query_one("#folder").value = "other"
        await pilot.pause()
        assert app.query_one("#custom_folder_box").display
        app.query_one("#folder").value = "Desktop"
        await pilot.pause()
        assert not app.query_one("#custom_folder_box").display

    drive(scenario)


def test_typing_a_missing_folder_shows_the_error_below_it(tmp_path):
    async def scenario(app, pilot):
        app.query_one("#folder").value = "other"
        app.query_one("#custom_folder").value = str(tmp_path / "missing")
        await pilot.pause()
        assert text(app, "#custom_folder_error") == "Enter a folder that exists"
        app.query_one("#custom_folder").value = str(tmp_path)
        await pilot.pause()
        assert text(app, "#custom_folder_error") == ""

    drive(scenario)


def test_download_goes_to_the_custom_folder(downloads, tmp_path, monkeypatch):
    video, _ = downloads
    monkeypatch.setenv("HOME", str(tmp_path))  # so "~" points into tmp_path
    (tmp_path / "clips").mkdir()

    async def scenario(app, pilot):
        app.query_one("#folder").value = "other"
        app.query_one("#custom_folder").value = "  ~/clips  "
        await download(app, pilot)

    drive(scenario)
    assert video.call_args.args[1] == str(tmp_path / "clips")


@pytest.mark.parametrize("folder", ["", "/no/such/folder"])
def test_missing_custom_folder_does_not_start_a_download(downloads, folder):
    video, audio = downloads

    async def scenario(app, pilot):
        app.query_one("#folder").value = "other"
        app.query_one("#custom_folder").value = folder
        await download(app, pilot)
        assert not box(app).display
        assert not app.query_one("#download").disabled

    drive(scenario)
    video.assert_not_called()
    audio.assert_not_called()


@pytest.mark.parametrize("command, shown", [(["picker"], True), (None, False)])
def test_browse_button_only_exists_with_a_folder_picker(monkeypatch, command, shown):
    monkeypatch.setattr("bajalo.tui.folder_picker_command", lambda: command)

    async def scenario(app, pilot):
        assert bool(app.query("#browse")) is shown

    drive(scenario)


async def browse(app, pilot):
    """Choose the custom folder, press Browse... and wait for the picker to answer."""
    app.query_one("#folder").value = "other"
    await pilot.pause()
    app.query_one("#browse").press()
    await pilot.pause()
    await app.workers.wait_for_complete()
    await pilot.pause()


def test_browse_fills_in_the_folder_chosen_in_the_picker(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "darwin")

    async def scenario(app, pilot):
        with patch("bajalo.tui.pick_folder", return_value=str(tmp_path)):
            await browse(app, pilot)
        assert app.query_one("#custom_folder").value == str(tmp_path)
        assert text(app, "#custom_folder_error") == ""
        assert not app.query_one("#browse").disabled

    drive(scenario)


def test_cancelling_the_picker_keeps_the_typed_folder(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")

    async def scenario(app, pilot):
        app.query_one("#custom_folder").value = "~/clips"
        with patch("bajalo.tui.pick_folder", return_value=None):
            await browse(app, pilot)
        assert app.query_one("#custom_folder").value == "~/clips"
        assert not app.query_one("#browse").disabled

    drive(scenario)


# --- calling the downloader -------------------------------------------------


def test_video_download_passes_the_form_values(downloads):
    video, audio = downloads

    async def scenario(app, pilot):
        await download(app, pilot, f"  {URL}  ")  # pasted with spaces around

    drive(scenario)
    video.assert_called_once()
    assert video.call_args.args == (
        URL,
        str(Path.home() / "Desktop"),
        FORMATS["1080p"],
        EXTENSIONS["mp4"],
    )
    assert video.call_args.kwargs["quiet"] is True
    audio.assert_not_called()


def test_audio_download_passes_the_form_values(downloads):
    video, audio = downloads

    async def scenario(app, pilot):
        app.query_one("#media_type").value = "audio"
        app.query_one("#folder").value = "Downloads"
        app.query_one("#audio_format").value = AUDIO_FORMATS["opus"]
        await download(app, pilot)

    drive(scenario)
    audio.assert_called_once()
    assert audio.call_args.args == (URL, str(Path.home() / "Downloads"), "opus")
    video.assert_not_called()


# --- progress ---------------------------------------------------------------


def test_progress_hook_moves_the_bar_and_title(downloads):
    video, _ = downloads
    seen = []

    async def scenario(app, pilot):
        bar = app.query_one("#progress", ProgressBar)

        def fake_download(*args, progress_hook, quiet):
            # runs in the worker thread, like yt-dlp would
            progress_hook(
                {"status": "downloading", "downloaded_bytes": 25, "total_bytes": 100}
            )
            app.call_from_thread(
                lambda: seen.append((box(app).border_title, bar.percentage))
            )
            progress_hook(
                {"status": "finished", "downloaded_bytes": 100, "total_bytes": 100}
            )
            app.call_from_thread(
                lambda: seen.append((box(app).border_title, bar.percentage))
            )
            return SAVED_TO

        video.side_effect = fake_download
        await download(app, pilot)

    drive(scenario)
    assert seen == [("Downloading...", 0.25), ("Processing...", 1.0)]


def test_missing_total_leaves_the_bar_indeterminate(downloads):
    video, _ = downloads
    totals = []

    async def scenario(app, pilot):
        bar = app.query_one("#progress", ProgressBar)

        def fake_download(*args, progress_hook, quiet):
            progress_hook({"status": "downloading", "downloaded_bytes": 10})
            app.call_from_thread(lambda: totals.append(bar.total))
            return SAVED_TO

        video.side_effect = fake_download
        await download(app, pilot)

    drive(scenario)
    assert totals == [None]


# --- result -----------------------------------------------------------------


def test_success_shows_where_the_file_was_saved(downloads):
    async def scenario(app, pilot):
        await download(app, pilot)
        assert box(app).border_title == "Completed"
        assert box(app).has_class("done")
        assert text(app, "#download_path") == f"Saved to: {SAVED_TO}"  # brackets kept
        assert not app.query_one("#download").disabled

    drive(scenario)


def test_failure_shows_the_clean_error_and_reenables_the_button(downloads):
    video, _ = downloads
    video.side_effect = DownloadError(
        "\x1b[0;31mERROR:\x1b[0m [generic] Unsupported URL"
    )

    async def scenario(app, pilot):
        await download(app, pilot)
        assert app.is_running
        assert box(app).border_title == "Failed"
        assert box(app).has_class("failed")
        assert text(app, "#download_error") == "ERROR: [generic] Unsupported URL"
        assert not app.query_one("#download").disabled

    drive(scenario)


def test_next_download_clears_the_previous_result(downloads):
    video, _ = downloads
    video.side_effect = [DownloadError("boom"), SAVED_TO]

    async def scenario(app, pilot):
        await download(app, pilot)
        assert box(app).has_class("failed")
        await download(app, pilot)
        assert not box(app).has_class("failed")
        assert box(app).has_class("done")
        assert box(app).border_title == "Completed"

    drive(scenario)


def test_clicking_the_saved_path_reveals_it_in_finder(downloads, monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")

    async def scenario(app, pilot):
        await download(app, pilot)
        assert app.query_one("#download_path").has_class("link")
        with patch("bajalo.utils.subprocess.Popen") as popen:
            await pilot.click("#download_path")
            await pilot.pause()
            await app.workers.wait_for_complete()
        assert popen.call_args.args[0] == ["open", "-R", SAVED_TO]

    drive(scenario)


def test_saved_path_is_plain_text_without_a_file_manager(downloads, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    async def scenario(app, pilot):
        await download(app, pilot)
        assert text(app, "#download_path") == f"Saved to: {SAVED_TO}"
        assert not app.query_one("#download_path").has_class("link")
        with patch("bajalo.utils.subprocess.Popen") as popen:
            await pilot.click("#download_path")
            await pilot.pause()
            await app.workers.wait_for_complete()
        popen.assert_not_called()

    drive(scenario)


# --- keys -------------------------------------------------------------------


def test_escape_quits_even_while_typing_the_url():
    async def scenario(app, pilot):
        app.query_one("#url").focus()
        await pilot.press("h", "o", "l", "a", "escape")
        await pilot.pause()
        assert not app.is_running

    drive(scenario)


def test_escape_first_closes_an_open_dropdown():
    async def scenario(app, pilot):
        app.query_one("#quality").focus()
        await pilot.press("enter")  # open the dropdown
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.is_running

    drive(scenario)


# --- theme ------------------------------------------------------------------


def test_starts_with_the_terminal_theme_when_nothing_is_saved():
    async def scenario(app, pilot):
        assert app.theme == "terminal"

    drive(scenario)


def test_changing_the_theme_saves_it(config_path):
    async def scenario(app, pilot):
        app.theme = "nord"
        await pilot.pause()

    drive(scenario)
    assert json.loads(config_path.read_text()) == {"theme": "nord"}


def test_changing_the_theme_keeps_the_other_saved_settings(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"folder": "/Users/me/Movies"}))

    async def scenario(app, pilot):
        app.theme = "nord"
        await pilot.pause()

    drive(scenario)
    assert json.loads(config_path.read_text()) == {
        "folder": "/Users/me/Movies",
        "theme": "nord",
    }


def test_starts_with_the_saved_theme(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"theme": "nord"}))

    async def scenario(app, pilot):
        assert app.theme == "nord"

    drive(scenario)


@pytest.mark.parametrize(
    "saved",
    [
        '{"theme": "nord"',  # broken JSON
        '{"theme": "no-such-theme"}',  # theme that doesn't exist
        "{}",  # no theme key
    ],
)
def test_falls_back_to_the_terminal_theme_when_the_saved_one_is_unusable(
    config_path, saved
):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(saved)

    async def scenario(app, pilot):
        assert app.theme == "terminal"

    drive(scenario)


# --- saved folder -----------------------------------------------------------


def save_folder(config_path, folder):
    """Pretend a previous run saved this folder."""
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"folder": folder}))


def test_download_saves_the_folder(downloads, config_path):
    async def scenario(app, pilot):
        app.query_one("#folder").value = "Downloads"
        await download(app, pilot)

    drive(scenario)
    saved = json.loads(config_path.read_text())
    assert saved["folder"] == str(Path.home() / "Downloads")


def test_invalid_folder_is_not_saved(downloads, config_path):
    async def scenario(app, pilot):
        app.query_one("#folder").value = "other"
        app.query_one("#custom_folder").value = "/no/such/folder"
        await download(app, pilot)

    drive(scenario)
    assert "folder" not in json.loads(config_path.read_text())


@pytest.mark.parametrize("name", ["Desktop", "Downloads"])
def test_starts_with_the_saved_preset_folder(config_path, name):
    save_folder(config_path, str(Path.home() / name))

    async def scenario(app, pilot):
        await pilot.pause()
        assert app.query_one("#folder").value == name
        assert not app.query_one("#custom_folder_box").display

    drive(scenario)


def test_starts_with_the_saved_custom_folder(config_path, tmp_path):
    save_folder(config_path, str(tmp_path))

    async def scenario(app, pilot):
        await pilot.pause()
        assert app.query_one("#folder").value == "other"
        assert app.query_one("#custom_folder").value == str(tmp_path)
        assert app.query_one("#custom_folder_box").display
        assert text(app, "#custom_folder_error") == ""

    drive(scenario)


def test_saved_folder_that_no_longer_exists_shows_the_error(config_path):
    save_folder(config_path, "/no/such/folder")

    async def scenario(app, pilot):
        await pilot.pause()
        assert app.query_one("#folder").value == "other"
        assert app.query_one("#custom_folder").value == "/no/such/folder"
        assert text(app, "#custom_folder_error") == "Enter a folder that exists"

    drive(scenario)
