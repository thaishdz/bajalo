from yt_dlp import YoutubeDL


def download_video(url, folder, quality, extension, progress_hook=None, quiet=False):
    options = {
        "paths": {"home": folder},
        "format": "bv*+ba/b",  # best video + best audio, or the best single file
        "format_sort": [quality],  # e.g. "res:1080": largest up to 1080p
    }
    if extension:
        options["merge_output_format"] = extension
    if extension == "mp4":  # prefer H.264/AAC so the mp4 plays everywhere,
        # even if that means a lower resolution than the one asked for
        options["format_sort"] = ["vcodec:h264", "acodec:aac", quality]

    return _download(url, options, progress_hook, quiet)


def download_audio(url, folder, audio_format, progress_hook=None, quiet=False):
    options = {
        "paths": {"home": folder},
        "format": "bestaudio/best",  # fetch only the audio track, not the full video
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,  # "best", "mp3", "m4a"...
            }
        ],
    }

    return _download(url, options, progress_hook, quiet)


def _download(url, options, progress_hook=None, quiet=False):
    if progress_hook:
        options["progress_hooks"] = [progress_hook]
    if quiet:
        options["quiet"] = True
        options["noprogress"] = True
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        return info["requested_downloads"][0]["filepath"]
