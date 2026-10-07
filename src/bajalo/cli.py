import sys
import questionary
from bajalo.downloader import download_video

FORMATS = {
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p":  "bv*[height<=720]+ba/b[height<=720]",
}

EXTENSIONS = {"auto (let yt-dlp decide)": None, "mp4": "mp4", "mkv": "mkv", "webm": "webm"}

def main():
    url = get_url()
    folder = get_folder()
    quality = get_quality()
    extension = get_extension()
    download_video(url, folder, quality, extension)


def get_url():
    return questionary.text("Paste the video URL:").ask() or sys.exit(1)


def get_folder():
    return questionary.select(
        "Save to:",
        choices=["Desktop", "Downloads"],
    ).ask() or sys.exit(1)

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