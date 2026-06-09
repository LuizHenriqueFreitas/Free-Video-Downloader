#services/updater.py

import os
import re
import requests
import shutil
from core.utils import get_ytdlp_path
import subprocess


YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

# ==========================
# VERSÃO DO APP / RELEASE NO GITHUB
# ==========================
APP_VERSION = "2.0.0"
GITHUB_REPO = "LuizHenriqueFreitas/Free-Video-Downloader"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(text):
    """'v2.1.0' -> (2, 1, 0). Ignora sufixos não numéricos."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) if nums else ()


def _is_newer(candidate, current):
    cv, curv = _parse_version(candidate), _parse_version(current)
    if not cv:
        return False
    # normaliza tamanhos (ex.: (2,1) vs (2,0,0))
    length = max(len(cv), len(curv))
    cv += (0,) * (length - len(cv))
    curv += (0,) * (length - len(curv))
    return cv > curv


def check_app_update():
    """
    Consulta a release mais recente do projeto no GitHub.
    Retorna (atualizacao_disponivel: bool, versao_mais_nova: str|None).
    Em caso de falha de rede/API, retorna (False, None) silenciosamente.
    """
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


def download_latest():
    ytdlp_path = get_ytdlp_path()
    temp_path = ytdlp_path + ".new"

    response = requests.get(YTDLP_DOWNLOAD_URL, stream=True, timeout=30)

    if response.status_code != 200:
        raise Exception("Falha ao baixar yt-dlp")

    with open(temp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return temp_path


def replace_binary(temp_path):
    ytdlp_path = get_ytdlp_path()
    backup_path = ytdlp_path + ".backup"

    if os.path.exists(ytdlp_path):
        shutil.move(ytdlp_path, backup_path)

    shutil.move(temp_path, ytdlp_path)

    if os.path.exists(backup_path):
        os.remove(backup_path)


def check_and_update():
    try:
        temp_file = download_latest()
        replace_binary(temp_file)
        return True, "yt-dlp atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar: {str(e)}"
    
def get_installed_version():
    try:
        result = subprocess.run(
            [get_ytdlp_path(), "--version"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()

        return "Erro"
    except:
        return "N/A"
