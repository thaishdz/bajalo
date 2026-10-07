from yt_dlp import YoutubeDL

def download_video(url, folder, video_format, extension):
    options = {
        "paths": {"home": folder},
        "format": video_format,
    }
    if extension:
        options["merge_output_format"] = extension
    if extension == "mp4":  # prefer H.264/AAC so the mp4 plays everywhere
        options["format_sort"] = ["vcodec:h264", "acodec:aac"]
    
    _download(url, options)


def download_audio(url, folder, audio_format):
    options = {
        "paths": {"home": folder},
        "format": "bestaudio/best", # fetch only the audio track, not the full video
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format, # "best", "mp3", "m4a"...
        }],
    }

    _download(url, options)

def _download(url, options):
    with YoutubeDL(options) as ydl:
        ydl.download([url])