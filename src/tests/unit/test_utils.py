import os
import sys
import pytest

from src.core import utils


# ==========================
# RESOURCE PATH
# ==========================

def test_resource_path_dev():
    path = utils.resource_path("test/file.txt")

    assert "test/file.txt" in path
    assert os.path.isabs(path)


def test_resource_path_pyinstaller(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", "/fake_bundle", raising=False)

    path = utils.resource_path("file.txt")

    assert path == os.path.join("/fake_bundle", "file.txt")


# ==========================
# YT-DLP PATH
# ==========================

def test_get_ytdlp_path():
    path = utils.get_ytdlp_path()

    if sys.platform == "win32":
        assert "yt-dlp.exe" in path
    else:
        assert "yt-dlp" in path

    # implement a metod to verify the embed folder "/bin/yt-dlp.exe"


# ==========================
# FFMPEG PATH
# ==========================

def test_get_ffmpeg_path():
    path = utils.get_ffmpeg_path()

    if sys.platform == "win32":
        assert "ffmpeg" in path.lower()
    else:
        assert "ffmpeg" in path


# ==========================
# NODE PATH
# ==========================

def test_get_node_path_exists(monkeypatch):

    path = utils.get_node_path()

    assert path is not None
    assert isinstance(path, str)
    assert os.access(path, os.X_OK)
    if sys.platform == "win32":
        assert path.endswith('.exe') or 'node' in path.lower()
    else:
        assert 'node' in path


def test_get_node_path_not_exists(monkeypatch):
    monkeypatch.setattr(utils, "resource_path", lambda x: "/fake/node.exe")
    monkeypatch.setattr(os.path, "exists", lambda x: False)

    with pytest.raises(Exception):
        utils.get_node_path()


# ==========================
# COOKIES PATH
# ==========================

def test_get_cookies_path():
    path = utils.get_cookies_path()

    assert "cookies.txt" in path


# ==========================
# COOKIES EXISTS
# ==========================

def test_cookies_exists_true(monkeypatch):
    monkeypatch.setattr(utils, "get_cookies_path", lambda: "/fake/cookies.txt")
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    assert utils.cookies_exists() is True


def test_cookies_exists_false(monkeypatch):
    monkeypatch.setattr(utils, "get_cookies_path", lambda: "/fake/cookies.txt")
    monkeypatch.setattr(os.path, "exists", lambda x: False)

    assert utils.cookies_exists() is False