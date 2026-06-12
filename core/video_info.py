# core/video_info.py

import subprocess
import json
import sys

from core.utils import get_ytdlp_path, get_cookies_path, cookies_exists, get_node_path, is_youtube


class VideoInfo:
    def extract(self, url: str):
        if not url:
            raise ValueError("URL vazia")

        ytdlp_path = get_ytdlp_path()
        node_path = get_node_path()

        # yt-dlp command line
        command = [ytdlp_path]

        # user-agent + extractor-args são específicos do YouTube. NÃO usar em
        # outras plataformas: o "Mozilla/5.0" causa HTTP 403 no TikTok.
        if is_youtube(url):
            command += [
                "--user-agent", "Mozilla/5.0",
                "--extractor-args", "youtube:player_client=web_safari,android_vr",
            ]

        command += [
            "--js-runtime", f"node:{node_path}",
            "--no-playlist",
            "--skip-download",
            "-j",
            url,
        ]

        # add cookies to yt-dlp command line
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # 🔥 Configuração para ocultar janela do console no Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=90,   # defensivo: não deixa a thread presa indefinidamente
            )
        except subprocess.TimeoutExpired:
            raise Exception("Tempo esgotado ao obter informações do vídeo")

        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        try:
            info = json.loads(result.stdout)
        except Exception:
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

    # ==========================
    # PLAYLIST
    # ==========================
    def extract_playlist(self, url: str):
        """
        Enumera os vídeos de uma playlist (rápido, sem baixar nada).
        Retorna {"title": str, "entries": [{"url", "title", "id", "duration"}, ...]}
        ou None se a URL não for uma playlist.
        """
        if not url:
            raise ValueError("URL vazia")

        ytdlp_path = get_ytdlp_path()

        command = [
            ytdlp_path,
            "--flat-playlist",
            "--no-warnings",
            "-J",
            url,
        ]
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            creationflags=creationflags,
        )

        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        try:
            info = json.loads(result.stdout)
        except Exception:
            raise Exception("Falha ao interpretar a playlist")

        entries = info.get("entries")
        if info.get("_type") != "playlist" or not entries:
            return None

        parsed = []
        for e in entries:
            if not e:
                continue
            entry_url = e.get("url") or e.get("webpage_url") or e.get("id")
            if entry_url and not str(entry_url).startswith("http"):
                # fallback: monta URL do YouTube a partir do id
                if is_youtube(url):
                    entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            # ADICIONAR THUMBNAIL
            # Para YouTube, a thumb pode ser montada a partir do ID
            thumb = e.get("thumbnail")
            if not thumb and is_youtube(url) and e.get("id"):
                # Monta URL da thumbnail do YouTube a partir do ID do vídeo
                vid_id = e.get("id")
                thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
            
            parsed.append({
                "url": entry_url,
                "title": e.get("title") or "(sem título)",
                "id": e.get("id"),
                "duration": e.get("duration"),
                "thumbnail": thumb,  # <-- ADICIONADO
            })

        return {
            "title": info.get("title", "Playlist"),
            "entries": parsed,
        }


# ==========================
# PREVIEW (URL TOCÁVEL)
# ==========================
def pick_preview_url(info: dict):
    """
    Escolhe, entre os formatos brutos, uma URL progressiva (vídeo+áudio juntos)
    para o QMediaPlayer. Prioriza a MENOR resolução progressiva em mp4 — o
    preview é só para o usuário visualizar onde cortar, então estabilidade
    importa mais que qualidade (a qualidade do download é a que o usuário
    selecionou, independente do preview). Retorna None se não houver formato
    progressivo.
    """
    if not info:
        return None

    formats = info.get("raw_formats") or info.get("formats") or []
    progressive = []
    for f in formats:
        if not isinstance(f, dict):
            continue
        if f.get("vcodec") in (None, "none"):
            continue
        if f.get("acodec") in (None, "none"):
            continue
        if not f.get("url"):
            continue
        proto = (f.get("protocol") or "").lower()
        is_hls = "m3u8" in proto
        progressive.append((f, is_hls))

    if not progressive:
        return None

    def score(item):
        f, is_hls = item
        height = f.get("height") or 9999
        not_hls = 0 if is_hls else 1            # prefere não-HLS (mais estável)
        is_mp4 = 1 if (f.get("ext") == "mp4") else 0
        # -height => a MENOR resolução vence (mais leve/estável p/ tocar)
        return (not_hls, is_mp4, -height)

    best = max(progressive, key=score)
    return best[0].get("url")