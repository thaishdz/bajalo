import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(text):
    parts = urlparse(text.strip())
    return parts.scheme in ("http", "https") and bool(parts.netloc)


# macOS: Finder's folder picker
MACOS_FOLDER_PICKER = 'POSIX path of (choose folder with prompt "Save to:")'

# Windows: the folder picker from .NET, kept above the terminal by a topmost owner
WINDOWS_FOLDER_PICKER = """
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true}
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = 'Save to:'
if ($dialog.ShowDialog($owner) -eq 'OK') { $dialog.SelectedPath }
"""


def has_desktop():
    """Linux: whether there's a graphical session to open windows in."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def folder_picker_command():
    """The command that opens a folder picker on this system, or None if there's none."""
    if sys.platform == "darwin":
        return ["osascript", "-e", MACOS_FOLDER_PICKER]
    if sys.platform == "win32":
        return ["powershell", "-NoProfile", "-Command", WINDOWS_FOLDER_PICKER]
    if not has_desktop():
        return None
    if shutil.which("zenity"):  # GNOME and most other desktops
        return ["zenity", "--file-selection", "--directory", "--title=Save to:"]
    if shutil.which("kdialog"):  # KDE
        return ["kdialog", "--getexistingdirectory", str(Path.home())]
    return None


def pick_folder():
    """Open the system's folder picker. The chosen path, or None on Cancel."""
    command = folder_picker_command()
    if command is None:
        return None
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    folder = result.stdout.strip()
    if result.returncode != 0 or not folder:
        return None
    return str(Path(folder))  # drops the trailing "/"


def reveal_command(path):
    """The command that shows `path` in the file manager, or None if there's none."""
    if sys.platform == "darwin":
        return ["open", "-R", path]  # Finder, with the file selected
    if sys.platform == "win32":
        return ["explorer", f"/select,{path}"]  # Explorer, with the file selected
    if not has_desktop():
        return None
    if shutil.which("gdbus"):
        # The freedesktop standard: Nautilus, Dolphin, Nemo... select the file
        uri = Path(path).absolute().as_uri()
        return [
            "gdbus", "call", "--session", "--timeout", "5",
            "--dest", "org.freedesktop.FileManager1",
            "--object-path", "/org/freedesktop/FileManager1",
            "--method", "org.freedesktop.FileManager1.ShowItems",
            f"['{uri}']", "",
        ]  # fmt: skip
    return open_folder_command(path)


def open_folder_command(path):
    """Linux: the command that opens the folder holding `path`, or None."""
    if shutil.which("xdg-open"):
        return ["xdg-open", str(Path(path).parent)]
    return None


def reveal_file(path):
    """Show `path` in the file manager. Waits for gdbus, so call it off the UI thread."""
    command = reveal_command(path)
    if command is not None and command[0] == "gdbus":
        result = subprocess.run(command, capture_output=True, check=False)
        if result.returncode == 0:
            return
        # No file manager implements ShowItems: open the folder instead
        command = open_folder_command(path)
    if command is not None:
        # Popen: some file managers keep xdg-open waiting until they close
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def is_existing_folder(folder_path):
    folder_path = folder_path.strip()
    return bool(folder_path) and Path(folder_path).expanduser().is_dir()
