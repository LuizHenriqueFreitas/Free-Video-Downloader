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

        # user-agent + extractor-args are especifics to YouTube. Don't use this
        # at outher plataforms: the "Mozilla/5.0" cause HTTP 403 on TikTok.
        if is_youtube(url):
            command += [
                "--user-agent", "Mozilla/5.0",
                "--extractor-args", "youtube:player_client=web_safari,android_vr", # this 2 player_client are the best for youtube 
            ]

        command += [
            "--js-runtime", f"node:{node_path}", # js-runtime is required at youtube bot detection
            "--no-playlist",
            "--skip-download",
            "-j",
            url,
        ]

        # add cookies to yt-dlp command line
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # Settings to not show windows console window
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=90,   # sytem defense: thread doesnt can stay running to infinity
            )
        except subprocess.TimeoutExpired:
            raise Exception("Time out to extract video info")

        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        try:
            info = json.loads(result.stdout)
        except Exception:
            raise Exception("Fail to read yt-dlp response")

        return self._format_response(info)

    # ==========================
    # FINAL FORMATATION
    # ==========================
    def _format_response(self, info: dict):
        formats = info.get("formats", [])

        # split audio and video
        video_formats = [
            f for f in formats
            if f.get("vcodec") != "none" and f.get("height")
        ]
        audio_formats = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none"
        ]

        # order by resolution and bitrate
        video_formats.sort(key=lambda x: x.get("height", 0))
        audio_formats.sort(key=lambda x: x.get("abr", 0))

        # remove duplicated by resolution+ext for videos, preserve size
        seen = set()
        unique_video_formats = []
        for f in reversed(video_formats): 
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
        unique_video_formats.reverse()  # smaller to bigger UI

        # remove duplicates by ext and bitrate for audios, preserving size
        seen_audio = set()
        unique_audio_formats = []
        for f in reversed(audio_formats):
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
        unique_audio_formats.reverse()  # smaller to bigger UI

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
            return "YouTube block"

        if "captcha" in s:
            return "YouTube block"

        if "429" in s:
            return "To much requisitions"

        if "cookies" in s:
            return "Error with cookies"

        if "unsupported" in s:
            return "URL not suported"

        if "private" in s:
            return "Private Video"

        if "sign in" in s:
            return "Login is required - Update your cookies"

        return stderr

    # ==========================
    # PLAYLIST
    # ==========================
    def extract_playlist(self, url: str):
        """
        Count playlist videos, fast without any donwload
        Return {"title": str, "entries": [{"url", "title", "id", "duration", "thumbnail"}, ...]}
        or None if the URL was not a playlist
        """
        if not url:
            raise ValueError("null URL")

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
            raise Exception("Fail to read playlist data")

        entries = info.get("entries")
        if info.get("_type") != "playlist" or not entries:
            return None

        parsed = []
        for e in entries:
            if not e:
                continue
            entry_url = e.get("url") or e.get("webpage_url") or e.get("id")
            if entry_url and not str(entry_url).startswith("http"):
                # fallback: build Youtube URL using ID
                if is_youtube(url):
                    entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            
            # ---- ENTRANCE THUMBNAIL ----
            thumb = e.get("thumbnail")
            if not thumb and is_youtube(url) and e.get("id"):
                # Build thumbnail URL using the video ID
                vid_id = e.get("id")
                thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
            
            parsed.append({
                "url": entry_url,
                "title": e.get("title") or "(sem título)",
                "id": e.get("id"),
                "duration": e.get("duration"),
                "thumbnail": thumb,
            })

        return {
            "title": info.get("title", "Playlist"),
            "entries": parsed,
        }


# ==========================
# PREVIEW (CHANGEABLE URL)
# ==========================
def pick_preview_url(info: dict):
    """
    Choose between the raw formats, a progressive URL (video+audio)
    used on QMediaPlayer, Priorize the smaller profressive resolution with mp4.
    Preview is useful only for the user view and cut, so estalibity is more 
    important tha quality here, the download quality is selected separeted.
    Return None if has'nt progressive format avalible.
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
        not_hls = 0 if is_hls else 1            # prefer non-HLS (more stable)
        is_mp4 = 1 if (f.get("ext") == "mp4") else 0
        # -height => the smaller resolution is more stable to play
        return (not_hls, is_mp4, -height)

    best = max(progressive, key=score)
    return best[0].get("url")