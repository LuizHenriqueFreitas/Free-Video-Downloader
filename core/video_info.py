import subprocess
import json


from core.utils import (
    get_ytdlp_path,
    get_cookies_path,
    cookies_exists
)


class VideoInfo:
    def extract(self, url: str):
        if not url:
            raise ValueError("URL vazia")

        ytdlp_path = get_ytdlp_path()

        command = [
            ytdlp_path,

            # 🔥 ESSENCIAL PRA YOUTUBE HOJE
            "--user-agent", "Mozilla/5.0",
            "--extractor-args", "youtube:player_client=android,web,tv",

            "--no-playlist",
            "--skip-download",
            "-j",
            url
        ]

        # 🔐 cookies (se existirem)
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        print("\n🔍 EXTRAINDO INFO:")
        print(" ".join(command), "\n")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
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

        # 🎯 filtra só vídeos com resolução
        video_formats = [
            f for f in formats
            if f.get("vcodec") != "none"
            and f.get("height")
        ]

        # 🎯 ordena por resolução
        video_formats.sort(key=lambda x: x.get("height", 0))

        # 🎯 remove duplicados (mesma resolução)
        seen = set()
        unique_formats = []

        for f in reversed(video_formats):  # começa do maior
            h = f.get("height")
            if h not in seen:
                seen.add(h)
                unique_formats.append({
                    "height": h,
                    "ext": f.get("ext"),
                    "format_id": f.get("format_id")
                })

        # ordena crescente pra UI
        unique_formats.reverse()

        return {
            "title": info.get("title", "Sem título"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "formats": unique_formats,
            "raw_formats": formats,  # útil pra debug
        }

    # ==========================
    # TRATAMENTO DE ERROS
    # ==========================
    def _parse_error(self, stderr: str):
        stderr = stderr.lower()

        if "confirm you’re not a bot" in stderr:
            return "YouTube bloqueou a requisição. Atualize seus cookies."

        if "429" in stderr:
            return "Muitas requisições. Aguarde alguns minutos."

        if "cookies" in stderr:
            return "Erro com cookies. Verifique ou atualize o cookies.txt."

        if "unsupported url" in stderr:
            return "URL não suportada."

        if "private video" in stderr:
            return "Vídeo privado."

        if "sign in" in stderr:
            return "É necessário estar logado (cookies)."

        return stderr.strip() or "Erro desconhecido ao obter informações"