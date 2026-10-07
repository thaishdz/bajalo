import sys
import questionary
from bajalo.downloader import download_video


def main():
    url = get_url()
    folder = get_folder()
    download_video(url, folder)


def get_url():
    return questionary.text("Paste the video URL:").ask() or sys.exit(1)


def get_folder():
    return questionary.select(
        "Save to:",
        choices=["Desktop", "Downloads"],
    ).ask() or sys.exit(1)
