from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from bajalo.cli import get_audio_format, get_folder, main, validate_folder
from bajalo.options import FOLDERS, FORMATS

URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
# The label of the custom-folder choice, whatever its text
CUSTOM = next(label for label, value in FOLDERS.items() if value == "other")


def answers(*values):
    """Fake questionary prompts whose .ask() return these values, in order."""
    return [MagicMock(**{"ask.return_value": value}) for value in values]


# --- get_audio_format -------------------------------------------------------


@pytest.mark.parametrize(
    "label, expected",
    [
        pytest.param("auto (keep original quality)", "best", id="auto"),
        pytest.param("mp3", "mp3", id="mp3"),
        pytest.param("m4a", "m4a", id="m4a"),
        pytest.param("opus", "opus", id="opus"),
    ],
)
def test_audio_format_returns_the_codec_not_the_label(label, expected):
    with patch("bajalo.cli.questionary.select", side_effect=answers(label)):
        assert get_audio_format() == expected


# --- get_folder -------------------------------------------------------------


def finder(returncode, stdout=""):
    """Fake osascript run: Finder's folder picker returning `stdout`."""
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def test_get_folder_returns_the_preset_folder_in_home():
    with patch("bajalo.cli.questionary.select", side_effect=answers("Downloads")):
        assert get_folder() == str(Path.home() / "Downloads")


def test_other_opens_finder_on_macos(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    with (
        patch("bajalo.cli.questionary.select", side_effect=answers(CUSTOM)),
        patch(
            "bajalo.utils.subprocess.run", return_value=finder(0, "/Users/me/clips/\n")
        ),
    ):
        assert get_folder() == "/Users/me/clips"


def test_cancelling_finder_exits(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    with (
        patch("bajalo.cli.questionary.select", side_effect=answers(CUSTOM)),
        patch("bajalo.utils.subprocess.run", return_value=finder(1)),
        pytest.raises(SystemExit),
    ):
        get_folder()


def test_other_asks_for_a_path_without_a_folder_picker(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    with (
        patch("bajalo.cli.questionary.select", side_effect=answers(CUSTOM)),
        patch("bajalo.cli.questionary.path", side_effect=answers("~/clips")) as path,
        patch("bajalo.utils.subprocess.run") as run,
    ):
        assert get_folder() == str(Path.home() / "clips")
    assert path.call_args.kwargs["validate"] is validate_folder
    run.assert_not_called()


def test_validate_folder_explains_what_is_wrong(tmp_path):
    assert validate_folder(str(tmp_path)) is True
    assert validate_folder(str(tmp_path / "missing")) == "Enter a folder that exists"


# --- main -------------------------------------------------------------------


def test_main_only_audio_auto_downloads_best_audio():
    # main() asks: kind (select), url (text), folder (select), audio format (select)
    selects = answers("only audio", "Downloads", "auto (keep original quality)")
    with (
        patch("bajalo.cli.questionary.select", side_effect=selects),
        patch("bajalo.cli.questionary.text", side_effect=answers(URL)),
        patch(
            "bajalo.cli.download_audio",
        ) as download_audio,
        patch("bajalo.cli.download_video") as download_video,
    ):
        main()

    download_audio.assert_called_once_with(URL, str(Path.home() / "Downloads"), "best")
    download_video.assert_not_called()


def test_main_ctrl_c_during_download_exits_cleanly(capsys):
    selects = answers("video", "Desktop", "720p", "mkv")
    with (
        patch("bajalo.cli.questionary.select", side_effect=selects),
        patch("bajalo.cli.questionary.text", side_effect=answers(URL)),
        patch("bajalo.cli.download_video", side_effect=KeyboardInterrupt),
        patch("bajalo.cli.download_audio"),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 130
    assert str(Path.home() / "Desktop") in capsys.readouterr().out


def test_main_video_desktop_1080p_mp4():
    selects = answers("video", "Desktop", "1080p", "mp4")
    with (
        patch("bajalo.cli.questionary.select", side_effect=selects),
        patch("bajalo.cli.questionary.text", side_effect=answers(URL)),
        patch("bajalo.cli.download_audio") as download_audio,
        patch("bajalo.cli.download_video") as download_video,
    ):
        main()

    download_video.assert_called_once_with(
        URL, str(Path.home() / "Desktop"), FORMATS["1080p"], "mp4"
    )
    download_audio.assert_not_called()
