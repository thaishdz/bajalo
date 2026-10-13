from pathlib import Path
from unittest.mock import MagicMock, patch
from bajalo.options import FORMATS
import pytest

from bajalo.cli import get_audio_format, main

URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"


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


# --- main -------------------------------------------------------------------


def test_main_only_audio_auto_downloads_best_audio():
    # main() asks: kind (select), url (text), folder (select), audio format (select)
    selects = answers("only audio", "Downloads", "auto (keep original quality)")
    with (
        patch("bajalo.cli.questionary.select", side_effect=selects),
        patch("bajalo.cli.questionary.text", side_effect=answers(URL)),
        patch("bajalo.cli.download_audio") as download_audio,
        patch("bajalo.cli.download_video") as download_video,
    ):
        main()

    download_audio.assert_called_once_with(URL, str(Path.home() / "Downloads"), "best")
    download_video.assert_not_called()


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
