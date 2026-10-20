from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(text):
    parts = urlparse(text.strip())
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def is_existing_folder(folder_path):
    folder_path = folder_path.strip()
    return bool(folder_path) and Path(folder_path).expanduser().is_dir()
