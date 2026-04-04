# core/video_info.py

import subprocess
import json
import sys

from core.utils import get_ytdlp_path, get_cookies_path, cookies_exists, get_node_path


class VideoInfo:
    def extract(self, url: str):
        if not url:
            raise ValueError("URL vazia")

        ytdlp_path = get_ytdlp_path()
        node_path = get_node_path()

        # yt-dlp command line
        command = [
            ytdlp_path,
            "--user-agent", "Mozilla/5.0",
            "--js-runtime", f"node:{node_path}",
            "--extractor-args", "youtube:player_client=web_safari,android_vr",
            "--no-playlist",
            "--skip-download",
            "-j",
            url
        ]

        # add cookies to yt-dlp command line
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        print("\n🔍 EXTRAINDO INFO:")  # debug
        print(" ".join(command), "\n")  # debug

        # 🔥 Configuração para ocultar janela do console no Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=creationflags   # <-- adicionado
        )

        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        try:
            info = json.loads(result.stdout)
        except Exception:
            print("STDOUT:", result.stdout)
            raise Exception("Falha ao interpretar resposta do yt-dlp")

        return self._format_response(info)

    # ==========================
    # FORMATAÇÃO FINAL
    # ==========================
    def _format_response(self, info: dict):
        formats = info.get("formats", [])

        # 🎯 separa vídeos e áudios
        video_formats = [
            f for f in formats
            if f.get("vcodec") != "none" and f.get("height")
        ]
        audio_formats = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none"
        ]

        # ordena por resolução ou bitrate
        video_formats.sort(key=lambda x: x.get("height", 0))
        audio_formats.sort(key=lambda x: x.get("abr", 0))

        # remove duplicados por resolução+ext para vídeos, preservando tamanho
        seen = set()
        unique_video_formats = []
        for f in reversed(video_formats):  # maior primeiro
            h = f.get("height")
            ext = f.get("ext")
            key = (h, ext)
            if key not in seen:
                seen.add(key)
                filesize = f.get("filesize") or f.get("filesize_approx")
                unique_video_formats.append({
                    "height": h,
                    "ext": ext,
                    "fps": f.get("fps"),
                    "format_id": f.get("format_id"),
                    "filesize": filesize,
                })
        unique_video_formats.reverse()  # menor para maior UI

        # remove duplicados por ext e bitrate para áudios, preservando tamanho
        seen_audio = set()
        unique_audio_formats = []
        for f in reversed(audio_formats):  # maior bitrate primeiro
            ext = f.get("ext")
            abr = f.get("abr")
            key = (ext, abr)
            if key not in seen_audio:
                seen_audio.add(key)
                filesize = f.get("filesize") or f.get("filesize_approx")
                unique_audio_formats.append({
                    "ext": ext,
                    "abr": abr,
                    "format_id": f.get("format_id"),
                    "filesize": filesize,
                })
        unique_audio_formats.reverse()  # menor para maior UI

        return {
            "title": info.get("title", "Sem título"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "formats": unique_video_formats,
            "audio_formats": unique_audio_formats,
            "raw_formats": formats,
        }

    # ==========================
    # ERRORS
    # ==========================
    def _parse_error(self, stderr: str) -> str:
        s = stderr.lower()

        if "confirm you're not a bot" in s:
            return "YouTube bloqueou"

        if "captcha" in s:
            return "YouTube bloqueou"

        if "429" in s:
            return "Muitas requisições"

        if "cookies" in s:
            return "Erro com cookies"

        if "unsupported" in s:
            return "URL não suportada"

        if "private" in s:
            return "Vídeo privado"

        if "sign in" in s:
            return "É necessário estar logado"

        return stderr