# services/updater.py

""" Maybe could be a good thing implement unit tests to this file.
    Also can be a good idea implementa an APP truly auto-updater.
"""

""" Here in this file you will find just some auto-update resoucers, like:
    - YT-DLP official repository url;
    - Get-Media-Free official repository url;
    - Function to check if there's a new version of Get-Media-Free;
    - App version validators;
    - YT-DLP auto updater, downloader and replacer;
    - YT-DLP version getter to be used on UI;
"""

import os
import re
import sys
import requests
import shutil
from core.i18n import tr
from core.utils import get_ytdlp_path, get_ytdlp_update_path
import subprocess

""" This file is resposable to mantain the app version, and the path to check
    and get new versions of the entair Get-Media-Free binary or just yt-dlp.exe
"""


""" ==================================================
    GET-MEDIA-FREE VERSION / YT=DLP / GITHUB RELEASE
  ================================================== """

# url to get yt-dlp last version from official github
# (Windows: standalone .exe | others: "yt-dlp" zipapp, needs python3 installed)
YTDLP_DOWNLOAD_URL = (
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if sys.platform == "win32" else
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
)

# Get Media Free actual version
APP_VERSION = "2.6.5"
# app oficial repo 
GITHUB_REPO = "LuizHenriqueFreitas/Get-Media-Free"
# github app releases api url
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


""" ============================
      APP VERSION VALIDATION
  =========================== """

# normalize release name just to numbers
# that will just work to x.x.x named releases, other names will not be catch by auto-updater
def _parse_version(text):
    #'v2.1.0' -> (2, 1, 0). Ignores non-numeric suffixes.
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) if nums else ()

# check is the newest github release is bigger (numericaly) than current version
def _is_newer(candidate, current):
    cv, curv = _parse_version(candidate), _parse_version(current)
    if not cv:
        return False
    # normalize sizes (ex.: (2,1) vs (2,0,0))
    length = max(len(cv), len(curv))
    cv += (0,) * (length - len(cv))
    curv += (0,) * (length - len(curv))
    return cv > curv


""" ========================
        CHECK APP UPDATE
  ======================== """

""" Checks the project's latest release on GitHub.
    Returns (update_available: bool, latest_version: str|None).
    In case of network or API failure, silently returns (False, None).

    That code just notifies that a new version avaliable, but doesn't auto update 
    the entire software yet.
"""
def check_app_update():
    try:
        r = requests.get(
            GITHUB_RELEASES_API,
            timeout=15,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code != 200:
            return (False, None)
        tag = (r.json().get("tag_name") or "").strip()
        latest = tag.lstrip("vV").strip() or tag
        if _is_newer(tag, APP_VERSION):
            return (True, latest)
        return (False, latest)
    except Exception:
        return (False, None)


""" =============================
        YT-DLP FUNCTIONS
  ========================= """

# as the name says, tha function download the lastest official ytdlp .exe
# it's saved at get_ytdlp_update_path() (user folder when installed), never on
# a system yt-dlp that get_ytdlp_path() could have found on PATH
def download_latest_ytdlp():
    ytdlp_path = get_ytdlp_update_path()
    os.makedirs(os.path.dirname(ytdlp_path), exist_ok=True)
    temp_path = ytdlp_path + ".new"

    response = requests.get(YTDLP_DOWNLOAD_URL, stream=True, timeout=30)

    if response.status_code != 200:
        raise Exception(tr("updater.download_failed"))

    with open(temp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    if sys.platform != "win32":
        os.chmod(temp_path, 0o755)

    return temp_path

# this function replaces the old version for the new one
def replace_binary_ytdlp(temp_path):
    ytdlp_path = get_ytdlp_update_path()
    backup_path = ytdlp_path + ".backup"

    # a leftover backup from an older update would block the move below
    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
        except OSError:
            pass

    # Windows can rename a running .exe (a download in progress) but not delete it
    if os.path.exists(ytdlp_path):
        os.replace(ytdlp_path, backup_path)

    try:
        shutil.move(temp_path, ytdlp_path)
    except OSError:
        # put the old one back, so yt-dlp keeps working
        if os.path.exists(backup_path):
            os.replace(backup_path, ytdlp_path)
        raise

    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
        except OSError:
            # still running: removed on the next update
            pass

""" This function implements the 2 other functinos above
    "download_lastest_ytdlp()" and "replace_binary_ytdlp()".
    Is that function how check and update the yt-dlp binary
"""
def check_and_update_ytdlp():
    try:
        temp_file = download_latest_ytdlp()
        replace_binary_ytdlp(temp_file)
        return True, tr("updater.ytdlp_updated")
    except Exception as e:
        return False, tr("updater.update_error", error=e)

# that is just a getter, this function get the actual version of ytdlp - probably used on UI
def get_installed_version_ytdlp():
    try:
        ytdlp_path = get_ytdlp_path()

        if os.path.isabs(ytdlp_path) and not os.path.exists(ytdlp_path):
                return tr("updater.not_found")
        
        # CREATE_NO_WINDOW: without it a console window flashes at the packaged app
        result = subprocess.run(
            [ytdlp_path, "--version"],
            capture_output=True,
            text=True,
            timeout = 10,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return tr("updater.version_error", error=result.stderr.strip())

    except FileNotFoundError as e:
        return tr("updater.ytdlp_not_found", error=e)
    except subprocess.TimeoutExpired:
        return tr("updater.timeout")
    except Exception as e:
        return tr("updater.unexpected_error", error=e)
