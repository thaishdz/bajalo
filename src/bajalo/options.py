FORMATS = {
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
}

EXTENSIONS = {
    "auto (let yt-dlp decide)": None,
    "mp4": "mp4",
    "mkv": "mkv",
    "webm": "webm",
}

FOLDERS = ["Desktop", "Downloads"]

AUDIO_FORMATS = {
    "auto (keep original quality)": "best",
    "mp3": "mp3",
    "m4a": "m4a",
    "opus": "opus",
}
