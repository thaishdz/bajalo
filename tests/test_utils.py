from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from bajalo.utils import (
    folder_picker_command,
    is_existing_folder,
    is_valid_url,
    pick_folder,
    reveal_command,
    reveal_file,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            "https://www.youtube.com/watch?v=YE7VzlLtp-4", True, id="youtube-https"
        ),
        pytest.param("http://example.com/video.mp4", True, id="plain-http"),
        pytest.param("  https://youtu.be/abc  ", True, id="surrounding-spaces"),
        pytest.param("youtube.com/watch?v=abc", False, id="no-scheme"),
        pytest.param("ftp://example.com/a", False, id="wrong-scheme"),
        pytest.param("https://", False, id="no-domain"),
        pytest.param("hola", False, id="plain-text"),
        pytest.param("", False, id="empty"),
        pytest.param("   ", False, id="only-spaces"),
    ],
)
def test_is_valid_url(text, expected):
    assert is_valid_url(text) is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param("{tmp}", True, id="existing-folder"),
        pytest.param("  {tmp}  ", True, id="surrounding-spaces"),
        pytest.param("~/clips", True, id="tilde"),
        pytest.param("{tmp}/missing", False, id="missing"),
        pytest.param("{tmp}/notes.txt", False, id="a-file"),
        pytest.param("", False, id="empty"),
        pytest.param("   ", False, id="only-spaces"),
    ],
)
def test_is_existing_folder(tmp_path, monkeypatch, text, expected):
    monkeypatch.setenv("HOME", str(tmp_path))  # so "~" points into tmp_path
    (tmp_path / "clips").mkdir()
    (tmp_path / "notes.txt").write_text("")
    assert is_existing_folder(text.format(tmp=tmp_path)) is expected


# --- system integration -----------------------------------------------------


@pytest.fixture
def linux(monkeypatch):
    """A Linux desktop session with the given tools installed."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    def install(*tools):
        monkeypatch.setattr(
            "bajalo.utils.shutil.which",
            lambda tool: f"/usr/bin/{tool}" if tool in tools else None,
        )

    return install


@pytest.mark.parametrize(
    "platform, program",
    [("darwin", "osascript"), ("win32", "powershell")],
)
def test_folder_picker_on_macos_and_windows(monkeypatch, platform, program):
    monkeypatch.setattr("sys.platform", platform)
    assert folder_picker_command()[0] == program


@pytest.mark.parametrize(
    "tools, program",
    [
        pytest.param(("zenity", "kdialog"), "zenity", id="prefers-zenity"),
        pytest.param(("kdialog",), "kdialog", id="kdialog"),
    ],
)
def test_folder_picker_on_linux(linux, tools, program):
    linux(*tools)
    assert folder_picker_command()[0] == program


def test_no_folder_picker_on_linux_without_tools(linux):
    linux()
    assert folder_picker_command() is None


def test_no_folder_picker_on_linux_without_a_desktop(linux, monkeypatch):
    linux("zenity")
    monkeypatch.delenv("DISPLAY")
    assert folder_picker_command() is None


@pytest.mark.parametrize(
    "returncode, stdout, expected",
    [
        pytest.param(0, "/Users/me/clips/\n", "/Users/me/clips", id="chosen"),
        pytest.param(1, "", None, id="cancel-macos-linux"),
        pytest.param(0, "\r\n", None, id="cancel-windows"),
    ],
)
def test_pick_folder(monkeypatch, returncode, stdout, expected):
    monkeypatch.setattr("sys.platform", "darwin")
    result = CompletedProcess(args=[], returncode=returncode, stdout=stdout)
    with patch("bajalo.utils.subprocess.run", return_value=result):
        assert pick_folder() == expected


def test_pick_folder_without_a_picker_opens_nothing(linux):
    linux()
    with patch("bajalo.utils.subprocess.run") as run:
        assert pick_folder() is None
    run.assert_not_called()


@pytest.mark.parametrize(
    "platform, expected",
    [
        ("darwin", ["open", "-R", "/clips/a.mp4"]),
        ("win32", ["explorer", "/select,/clips/a.mp4"]),
    ],
)
def test_reveal_selects_the_file_on_macos_and_windows(monkeypatch, platform, expected):
    monkeypatch.setattr("sys.platform", platform)
    assert reveal_command("/clips/a.mp4") == expected


def test_reveal_asks_the_file_manager_over_dbus_on_linux(linux):
    linux("gdbus", "xdg-open")
    command = reveal_command("/clips/my clip.mp4")
    assert command[0] == "gdbus"
    assert "org.freedesktop.FileManager1.ShowItems" in command
    assert "['file:///clips/my%20clip.mp4']" in command


def test_reveal_opens_the_folder_on_linux_without_gdbus(linux):
    linux("xdg-open")
    assert reveal_command("/clips/a.mp4") == ["xdg-open", "/clips"]


def test_no_reveal_on_linux_without_tools(linux):
    linux()
    assert reveal_command("/clips/a.mp4") is None


def dbus(returncode):
    """Fake gdbus run: 0 when a file manager answered ShowItems."""
    return CompletedProcess(args=[], returncode=returncode)


def test_reveal_file_stops_when_the_file_manager_answers(linux):
    linux("gdbus", "xdg-open")
    with (
        patch("bajalo.utils.subprocess.run", return_value=dbus(0)) as run,
        patch("bajalo.utils.subprocess.Popen") as popen,
    ):
        reveal_file("/clips/a.mp4")
    assert run.call_args.args[0][0] == "gdbus"
    popen.assert_not_called()


def test_reveal_file_opens_the_folder_when_dbus_fails(linux):
    linux("gdbus", "xdg-open")
    with (
        patch("bajalo.utils.subprocess.run", return_value=dbus(1)),
        patch("bajalo.utils.subprocess.Popen") as popen,
    ):
        reveal_file("/clips/a.mp4")
    assert popen.call_args.args[0] == ["xdg-open", "/clips"]


def test_reveal_file_does_nothing_when_dbus_fails_without_xdg_open(linux):
    linux("gdbus")
    with (
        patch("bajalo.utils.subprocess.run", return_value=dbus(1)),
        patch("bajalo.utils.subprocess.Popen") as popen,
    ):
        reveal_file("/clips/a.mp4")
    popen.assert_not_called()
