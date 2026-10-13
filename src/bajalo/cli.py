import sys
from pathlib import Path

import questionary
from yt_dlp.utils import DownloadError

from bajalo.downloader import download_audio, download_video
from bajalo.options import AUDIO_FORMATS, EXTENSIONS, FOLDERS, FORMATS
from bajalo.utils import is_valid_url


def main():
    media_type = get_media_type()
    url = get_url()
    folder = get_folder()
    try:
        if media_type == "video":
            download_video(url, folder, get_quality(), get_extension())
        else:
            download_audio(url, folder, get_audio_format())
    except DownloadError:
        print("Download failed. Check the link and try again.")
        sys.exit(1)
    except KeyboardInterrupt:
        print(
            f"\nDownload cancelled. Partial files may remain in {folder}.\n"
            "Run 'bajalo' again with the same URL to resume."
        )
        sys.exit(130)


def get_url():
    return questionary.text(
        "Paste the video URL:", validate=validate_url
    ).ask() or sys.exit(1)


def validate_url(text):
    return is_valid_url(text) or "Enter a full URL starting with http:// or https://"


def get_media_type():
    return questionary.select(
        "Select:", choices=["video", "only audio"]
    ).ask() or sys.exit(1)


def get_folder():
    choice = questionary.select(
        "Save to:",
        choices=FOLDERS,
    ).ask() or sys.exit(1)
    return str(Path.home() / choice)


def get_quality():
    choice = questionary.select(
        "Select quality:", choices=list(FORMATS)
    ).ask() or sys.exit(1)
    return FORMATS[choice]


def get_extension():
    choice = questionary.select(
        "Select extension:", choices=list(EXTENSIONS)
    ).ask() or sys.exit(1)
    return EXTENSIONS[choice]


def get_audio_format():
    choice = questionary.select(
        "Select audio format:",
        choices=list(AUDIO_FORMATS),
    ).ask() or sys.exit(1)
    return AUDIO_FORMATS[choice]
