#services/updater
import os
import requests
import shutil
from core.utils import get_ytdlp_path
import subprocess


YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


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
