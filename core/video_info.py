import subprocess
import json
from core.utils import get_ytdlp_path


class VideoInfo:
    def extract(self, url):
        if not url:
            raise ValueError("URL vazia")

        command = [
            get_ytdlp_path(),
            "-j",
            url
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"Erro ao extrair informações:\n{result.stderr}")

        try:
            info = json.loads(result.stdout)
        except Exception:
            raise Exception("Falha ao interpretar resposta do yt-dlp")

        return {
            "title": info.get("title", "Sem título"),
            "thumbnail": info.get("thumbnail"),
            "formats": info.get("formats", []),
            "height": info.get("height"),
        }