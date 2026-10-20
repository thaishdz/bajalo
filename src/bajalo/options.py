# yt-dlp sort keys: "res" is the short side, so vertical videos match too
FORMATS = {
    "1080p": "res:1080",
    "720p": "res:720",
}

EXTENSIONS = {
    "auto (let yt-dlp decide)": None,
    "mp4": "mp4",
    "mkv": "mkv",
    "webm": "webm",
}

FOLDERS = {"Desktop": "Desktop", "Downloads": "Downloads", "Custom Folder": "other"}

AUDIO_FORMATS = {
    "auto (keep original quality)": "best",
    "mp3": "mp3",
    "m4a": "m4a",
    "opus": "opus",
}
