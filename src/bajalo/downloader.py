from pathlib import Path
from yt_dlp import YoutubeDL

def download_video(url, folder_destination, video_format, extension):
    folder_destination = str(Path.home() / folder_destination)
    options = {
        "paths": {"home": folder_destination},
        "format": video_format,
    }

    if extension:
        options["merge_output_format"] = extension
    if extension == "mp4":  # prefer H.264/AAC so the mp4 plays everywhere
        options["format_sort"] = ["vcodec:h264", "acodec:aac"]
    
    with YoutubeDL(options) as ydl:
        ydl.download([url])
