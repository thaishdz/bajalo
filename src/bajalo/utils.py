import subprocess
from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(text):
    parts = urlparse(text.strip())
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def choose_folder_in_finder():
    """macOS: open Finder's folder picker. The chosen path, or None on Cancel."""
    result = subprocess.run(
        ["osascript", "-e", 'POSIX path of (choose folder with prompt "Save to:")'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return str(Path(result.stdout.strip()))  # drops the trailing "/"


def is_existing_folder(folder_path):
    folder_path = folder_path.strip()
    return bool(folder_path) and Path(folder_path).expanduser().is_dir()
