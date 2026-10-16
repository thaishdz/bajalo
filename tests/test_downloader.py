from unittest.mock import patch

import pytest
from yt_dlp.utils import DownloadError

from bajalo.downloader import download_audio, download_video

URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
FOLDER = "/home/user/Downloads"
QUALITY = "res:720"


@pytest.fixture
def ydl_cls():
    """Replace YoutubeDL with a fake so no real download happens."""
    with patch("bajalo.downloader.YoutubeDL") as cls:
        yield cls


def options_used(cls):
    """The options dict the code passed to YoutubeDL(...)."""
    return cls.call_args.args[0]


def ydl_instance(cls):
    """The fake `ydl` object the code gets inside `with YoutubeDL(...) as ydl`."""
    return cls.return_value.__enter__.return_value


def finished_download(cls, filepath):
    """Make extract_info report that yt-dlp saved the file at `filepath`."""
    ydl_instance(cls).extract_info.return_value = {
        "requested_downloads": [{"filepath": filepath}]
    }


# --- download_video ---------------------------------------------------------


def test_video_downloads_the_url(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    ydl_instance(ydl_cls).extract_info.assert_called_once_with(URL, download=True)


def test_video_returns_the_final_file_path(ydl_cls):
    finished_download(ydl_cls, "/home/user/Downloads/clip [abc].mp4")
    path = download_video(URL, FOLDER, QUALITY, "mp4")
    assert path == "/home/user/Downloads/clip [abc].mp4"


def test_video_sets_folder_format_and_quality(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    options = options_used(ydl_cls)
    assert options["paths"] == {"home": FOLDER}
    assert options["format"] == "bv*+ba/b"
    assert options["format_sort"] == [QUALITY]


def test_video_auto_container_adds_no_extra_options(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    options = options_used(ydl_cls)
    assert "merge_output_format" not in options
    assert options["format_sort"] == [QUALITY]


@pytest.mark.parametrize("extension", ["mkv", "webm"])
def test_video_other_containers_only_set_merge_format(ydl_cls, extension):
    download_video(URL, FOLDER, QUALITY, extension)
    options = options_used(ydl_cls)
    assert options["merge_output_format"] == extension
    assert options["format_sort"] == [QUALITY]


def test_video_mp4_prefers_h264_and_aac_over_quality(ydl_cls):
    download_video(URL, FOLDER, QUALITY, "mp4")
    options = options_used(ydl_cls)
    assert options["merge_output_format"] == "mp4"
    assert options["format_sort"] == ["vcodec:h264", "acodec:aac", QUALITY]


def test_video_uses_ydl_as_context_manager(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    ydl_cls.return_value.__enter__.assert_called_once()
    ydl_cls.return_value.__exit__.assert_called_once()


def test_video_passes_progress_hook_to_ydl(ydl_cls):
    def dummy_hook(d):
        pass

    download_video(URL, FOLDER, QUALITY, None, progress_hook=dummy_hook)
    options = options_used(ydl_cls)
    assert options["progress_hooks"] == [dummy_hook]


def test_video_without_hook_adds_no_progress_hooks(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    options = options_used(ydl_cls)
    assert "progress_hooks" not in options


def test_video_quiet_silences_ydl_output(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None, quiet=True)
    options = options_used(ydl_cls)
    assert options["quiet"] is True
    assert options["noprogress"] is True


def test_video_not_quiet_by_default(ydl_cls):
    download_video(URL, FOLDER, QUALITY, None)
    options = options_used(ydl_cls)
    assert "quiet" not in options
    assert "noprogress" not in options


# --- download_audio ---------------------------------------------------------


def test_audio_downloads_the_url(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    ydl_instance(ydl_cls).extract_info.assert_called_once_with(URL, download=True)


def test_audio_returns_the_converted_file_path(ydl_cls):
    # yt-dlp reports the path after FFmpegExtractAudio, e.g. .mp3 rather than .m4a
    finished_download(ydl_cls, "/home/user/Downloads/song.mp3")
    path = download_audio(URL, FOLDER, "mp3")
    assert path == "/home/user/Downloads/song.mp3"


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


def test_audio_passes_progress_hook_to_ydl(ydl_cls):
    def dummy_hook(d):
        pass

    download_audio(URL, FOLDER, "mp3", progress_hook=dummy_hook)
    options = options_used(ydl_cls)
    assert options["progress_hooks"] == [dummy_hook]


def test_audio_without_hook_adds_no_progress_hooks(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    options = options_used(ydl_cls)
    assert "progress_hooks" not in options


def test_audio_quiet_silences_ydl_output(ydl_cls):
    download_audio(URL, FOLDER, "mp3", quiet=True)
    options = options_used(ydl_cls)
    assert options["quiet"] is True
    assert options["noprogress"] is True


def test_audio_not_quiet_by_default(ydl_cls):
    download_audio(URL, FOLDER, "mp3")
    options = options_used(ydl_cls)
    assert "quiet" not in options
    assert "noprogress" not in options


# --- errors -----------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: download_video(URL, FOLDER, QUALITY, None),
        lambda: download_audio(URL, FOLDER, "mp3"),
    ],
    ids=["video", "audio"],
)
def test_download_errors_reach_the_caller(ydl_cls, call):
    """cli.main() catches DownloadError, so the downloader must not swallow it."""
    ydl_instance(ydl_cls).extract_info.side_effect = DownloadError("boom")
    with pytest.raises(DownloadError):
        call()
