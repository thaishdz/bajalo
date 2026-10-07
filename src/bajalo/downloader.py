from pathlib import Path
from yt_dlp import YoutubeDL

def download_video(url, folder_destination):
    print("downloader", url)
    destination = str(Path.home() / folder_destination)
    options = {"paths": {"home": destination}}
    with YoutubeDL(options) as ydl:
        ydl.download([url])


