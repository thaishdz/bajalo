import sys
import questionary
from pathlib import Path
from yt_dlp.utils import DownloadError
from bajalo.utils import is_valid_url
from bajalo.downloader import download_video, download_audio

FORMATS = {
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p":  "bv*[height<=720]+ba/b[height<=720]",
}

EXTENSIONS = {"auto (let yt-dlp decide)": None, "mp4": "mp4", "mkv": "mkv", "webm": "webm"}

def main():
    try:
        if get_kind() == "video":
            download_video(get_url(), get_folder(), get_quality(), get_extension())
        else:
            download_audio(get_url(), get_folder(), get_audio_format())
    except DownloadError:
        print("Download failed. Check the link and try again.")
        sys.exit(1)
    

def get_url():
    return questionary.text("Paste the video URL:", validate=validate_url).ask() or sys.exit(1)

def validate_url(text):
    return is_valid_url(text) or "Enter a full URL starting with http:// or https://"

def get_kind():
    return questionary.select(
        "Select:",
        choices=["video", "only audio"]).ask() or sys.exit(1)

def get_folder():
    choice = questionary.select(
        "Save to:",
        choices=["Desktop", "Downloads"],
    ).ask() or sys.exit(1)
    return str(Path.home() / choice)

def get_quality():
    choice = questionary.select(
        "Select quality:",
        choices=list(FORMATS)
    ).ask() or sys.exit(1)
    return FORMATS[choice]


def get_extension():
    choice= questionary.select(
        "Select extension:",
        choices=list(EXTENSIONS)
    ).ask() or sys.exit(1)
    return EXTENSIONS[choice]

def get_audio_format():
    return questionary.select(
        "Select audio format:",
        choices=[
            questionary.Choice("auto (keep original quality)", value="best"),
            "mp3",
            "m4a",
            "opus",
        ],
    ).ask() or sys.exit(1)
