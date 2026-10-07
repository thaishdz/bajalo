from unittest.mock import patch
import pytest
from yt_dlp.utils import DownloadError
from bajalo.downloader import download_audio, download_video

URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
FOLDER = "/home/user/Downloads"
SELECTOR = "bv*[height<=720]+ba/b[height<=720]"


@pytest.fixture
def ydl_cls():
    """Replace YoutubeDL with a fake so no real download happens."""
    with patch("bajalo.downloader.YoutubeDL") as cls:
        yield cls


def options_used(cls):
    """The options dict the code passed to YoutubeDL(...)."""
    return cls.call_args.args[0]


def download_called_with(cls):
    """The arguments the code passed to ydl.download(...), inside the `with`."""
    instance = cls.return_value.__enter__.return_value
    return instance.download.call_args.args


# --- download_video ---------------------------------------------------------

def test_video_passes_url_as_a_list(ydl_cls):
    download_video(URL, FOLDER, SELECTOR, None)
    assert download_called_with(ydl_cls) == ([URL],)


def test_video_sets_folder_and_format(ydl_cls):
    download_video(URL, FOLDER, SELECTOR, None)
    options = options_used(ydl_cls)
    assert options["paths"] == {"home": FOLDER}
    assert options["format"] == SELECTOR


def test_video_auto_container_adds_no_extra_options(ydl_cls):
    download_video(URL, FOLDER, SELECTOR, None)
    options = options_used(ydl_cls)
    assert "merge_output_format" not in options
    assert "format_sort" not in options


@pytest.mark.parametrize("extension", ["mkv", "webm"])
def test_video_other_containers_only_set_merge_format(ydl_cls, extension):
    download_video(URL, FOLDER, SELECTOR, extension)
    options = options_used(ydl_cls)
    assert options["merge_output_format"] == extension
    assert "format_sort" not in options


def test_video_mp4_prefers_h264_and_aac(ydl_cls):
    download_video(URL, FOLDER, SELECTOR, "mp4")
    options = options_used(ydl_cls)
    assert options["merge_output_format"] == "mp4"
    assert options["format_sort"] == ["vcodec:h264", "acodec:aac"]


def test_video_uses_ydl_as_context_manager(ydl_cls):
    download_video(URL, FOLDER, SELECTOR, None)
    ydl_cls.return_value.__enter__.assert_called_once()
    ydl_cls.return_value.__exit__.assert_called_once()


# --- download_audio ---------------------------------------------------------

def test_audio_passes_url_as_a_list(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    assert download_called_with(ydl_cls) == ([URL],)


def test_audio_sets_folder_and_best_audio_format(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    options = options_used(ydl_cls)
    assert options["paths"] == {"home": FOLDER}
    assert options["format"] == "bestaudio/best"


@pytest.mark.parametrize("codec", ["mp3", "m4a", "opus", "best"])
def test_audio_sends_codec_to_the_extract_audio_postprocessor(ydl_cls, codec):
    download_audio(URL, FOLDER, codec)
    assert options_used(ydl_cls)["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": codec}
    ]


def test_audio_uses_ydl_as_context_manager(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    ydl_cls.return_value.__enter__.assert_called_once()
    ydl_cls.return_value.__exit__.assert_called_once()


# --- errors -----------------------------------------------------------------

@pytest.mark.parametrize("call", [
    lambda: download_video(URL, FOLDER, SELECTOR, None),
    lambda: download_audio(URL, FOLDER, "mp3"),
])
def test_download_errors_reach_the_caller(ydl_cls, call):
    """cli.main() catches DownloadError, so the downloader must not swallow it."""
    instance = ydl_cls.return_value.__enter__.return_value
    instance.download.side_effect = DownloadError("boom")
    with pytest.raises(DownloadError):
        call()
