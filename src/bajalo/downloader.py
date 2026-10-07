from yt_dlp import YoutubeDL


def download_video(url):
    with YoutubeDL() as ydl:
        ydl.download([url])