# core/video_info.py

""" Here you will find:
    - Extract() function to extract video information from any plataform.
    - Format_Response() which one format the Extract() out to send UI.
    - Extract_Playlist() how is specificaly focused to extract youtube playlist data and format to send UI.
    - PreviewDownloader, it downloads a small local video (with sound) for the trimmer tool player.
"""

import os
import glob
import subprocess
import json
import sys

from core.i18n import tr
# import some funcions from utils.py
from core.utils import ( get_ytdlp_path, get_cookies_path, cookies_exists,
                        get_node_path, get_ffmpeg_path, is_youtube,
                        YOUTUBE_CLIENT_SETTINGS )

# main class of that file.
class VideoInfo:
    # JUST TO EXTRACT JSON INFO. where yt-dlp commandline is created. 
    def extract(self, url: str):
        if not url:
            raise ValueError(tr("video.empty_url"))

        # instanciate ytdlp and node paths
        ytdlp_path = get_ytdlp_path()
        node_path = get_node_path()

        # start yt-dlp command line
        command = [ytdlp_path]

        """ User-agent + extractor-args are especifics to YouTube. Don't use this
            at outher plataforms: the "Mozilla/5.0" cause HTTP 403 on TikTok. 
        """
        if is_youtube(url):
            command += ["--user-agent", "Mozilla/5.0"]
            # client settings (can be an empty list, see utils.py)
            command += YOUTUBE_CLIENT_SETTINGS

        # beeing a youtube link or not
        command += [
            "--js-runtimes", f"node:{node_path}", # js-runtime is required at youtube bot detection
            "--no-playlist",
            "--skip-download",
            "-j",
            url,
        ]

        # if there is a cookies.txt file, add cookies to yt-dlp command line
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # Settings to not show console window at Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                timeout=90,
            )
        except subprocess.TimeoutExpired:
            raise Exception(tr("video.extract_failed"))

        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        try:
            info = json.loads(result.stdout)
        except Exception:
            raise Exception(tr("video.read_response_failed"))

        return self._format_response(info)


    """ ==========================
        FINAL FORMATATION
       ========================== """
    
    # extract() function formating responde to sent to UI
    def _format_response(self, info: dict):
        formats = info.get("formats", [])
        duration = info.get("duration") or 0

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
        # "or 0" instead of get(key, 0): some formats have the key with None value
        # (ex.: HLS audio formats), and sort() can't compare None
        video_formats.sort(key=lambda x: x.get("height") or 0)
        audio_formats.sort(key=lambda x: x.get("abr") or 0)

        """ For each resolution, pick the same tracks yt-dlp will download
            (see "-S res,vcodec:h264,acodec:aac" at download_worker.py), so the size
            shown on the dialog is the real download size:
              - video: H.264 (avc1) first, then fps, then bitrate;
              - audio: AAC (mp4a) first, then bitrate - only if the video track
                doesn't have audio already (other sites may deliver both together).
            HLS (m3u8) formats are skipped when there are direct ones: yt-dlp
            prefers direct https downloads. "-drc" youtube tracks go last,
            yt-dlp also leaves them as last option.
        """
        best_audio = self._pick_audio(audio_formats)

        unique_video_formats = []
        for h in sorted({f.get("height") for f in video_formats}):
            candidates = self._prefer_direct([f for f in video_formats if f.get("height") == h])
            video = max(candidates, key=lambda f: (
                self._is_h264(f),
                not self._is_drc(f),
                f.get("fps") or 0,
                f.get("tbr") or 0,
            ))

            # video tracks without audio will be merged with the best audio
            has_audio = video.get("acodec") not in (None, "none")
            audio = None if has_audio else best_audio

            # total size = video + audio (None if some part is unknown)
            filesize = self._estimate_size(video, duration)
            if filesize is not None and audio is not None:
                audio_size = self._estimate_size(audio, duration)
                filesize = filesize + audio_size if audio_size is not None else None

            unique_video_formats.append({
                "height": h,
                "ext": video.get("ext"),
                "fps": video.get("fps"),
                "format_id": video.get("format_id"),
                "audio_format_id": audio.get("format_id") if audio else None,
                "filesize": filesize,
                # False = the site doesn't offer H.264 at this resolution, the
                # download will need to be converted (see download_worker.py)
                # None = the site doesn't inform the codec (can't know before)
                "h264": self._is_h264(video) if video.get("vcodec") else None,
            })

        # remove duplicateds by ext and bitrate for audios, preserving size
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
        unique_audio_formats.reverse()  # smaller to bigger at UI

        return {
            "title": info.get("title") or tr("common.untitled"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "formats": unique_video_formats,
            "audio_formats": unique_audio_formats,
            "raw_formats": formats,
        }


    """ ==========================
        FORMAT SELECTION HELPERS
        used by _format_response() to mirror yt-dlp choice
      ========================== """

    # True if the format video codec is H.264 (avc1)
    @staticmethod
    def _is_h264(f):
        return (f.get("vcodec") or "").startswith(("avc1", "h264"))

    # youtube "-drc" (dynamic range compression) audio tracks
    @staticmethod
    def _is_drc(f):
        return str(f.get("format_id") or "").endswith("-drc")

    # keep only direct (non HLS) formats, if there's at least one of them
    @staticmethod
    def _prefer_direct(fmts):
        direct = [f for f in fmts if "m3u8" not in (f.get("protocol") or "")]
        return direct or fmts

    # best audio track: AAC first, non "-drc", then bitrate
    def _pick_audio(self, audio_formats):
        if not audio_formats:
            return None
        candidates = self._prefer_direct(audio_formats)
        return max(candidates, key=lambda f: (
            (f.get("acodec") or "").startswith("mp4a"),
            not self._is_drc(f),
            f.get("abr") or 0,
        ))

    # track size in bytes: real size, yt-dlp approximation or bitrate * duration
    @staticmethod
    def _estimate_size(f, duration):
        size = f.get("filesize") or f.get("filesize_approx")
        if not size and f.get("tbr") and duration:
            # tbr is kbit/s
            size = f["tbr"] * 1000 / 8 * duration
        return int(size) if size else None


    """ ==========================
        ERRORS FAST RESPONSE
      ========================== """
    
    # known yt-dlp errors (stderr is always english) to a short friendly message
    def _parse_error(self, stderr: str) -> str:
        s = stderr.lower()

        if "confirm you're not a bot" in s:
            return tr("video.blocked_by_youtube")

        if "captcha" in s:
            return tr("video.blocked_by_youtube")

        if "429" in s:
            return tr("video.too_many_requests")

        if "cookies" in s:
            return tr("video.cookies_error")

        if "unsupported" in s:
            return tr("video.unsupported_link")

        if "private" in s:
            return tr("video.private")

        if "sign in" in s:
            return tr("video.login_required")

        return stderr


    """ ==========================
        PLAYLIST EXTRACT CONFIGURATION
      ========================== """

    # Playlist extract data function.
    """ Count playlist videos, fast without any donwload.
        Return {"title": str, "entries": [{"url", "title", "id", "duration", "thumbnail"}, ...]}
        or None if the URL was not a playlist.
    """
    def extract_playlist(self, url: str):
        if not url:
            raise ValueError("null URL")

        # get ytdlp path
        ytdlp_path = get_ytdlp_path()

        # start the ytdlp command line
        command = [
            ytdlp_path,
            "--flat-playlist", # allow playlists
            "--no-warnings",
            "-J",
            url,
        ]

        # check if cookies exists and add to command line
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # windows ux function to doesn't create console windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        # process the data information
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        # if doesn't result return 0 check for errors
        if result.returncode != 0:
            raise Exception(self._parse_error(result.stderr))

        # try to read the playlist data or get an exception
        try:
            info = json.loads(result.stdout)
        except Exception:
            raise Exception(tr("video.read_playlist_failed"))

        # filter plylist videos
        entries = info.get("entries")
        if info.get("_type") != "playlist" or not entries:
            return None

        # final list of playlist videos
        parsed = []
        for e in entries:
            if not e:
                continue
            # check video url
            entry_url = e.get("url") or e.get("webpage_url") or e.get("id")
            if entry_url and not str(entry_url).startswith("http"):
                # fallback: build Youtube URL using ID
                if is_youtube(url):
                    entry_url = f"https://www.youtube.com/watch?v={entry_url}"
            
            # get 1 by 1 thumbnail
            thumb = e.get("thumbnail")
            if not thumb and is_youtube(url) and e.get("id"):
                # Build thumbnail URL using the video ID
                vid_id = e.get("id")
                thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"

            # add video and video info to final list
            parsed.append({
                "url": entry_url,
                "title": e.get("title") or tr("common.untitled_entry"),
                "id": e.get("id"),
                "duration": e.get("duration"),
                "thumbnail": thumb,
            })

        # returns the titles and playlist content process data to UI.
        return {
            "title": info.get("title", "Playlist"),
            "entries": parsed,
        }


""" ==========================
    PREVIEW (LOCAL LOW QUALITY FILE)
    - before any download
   ========================== """

""" Download a small version (video + audio) of the media to be played on
    the trimmer tool (QMediaPlayer).
    Playing the site url directly doesn't work anymore: youtube doesn't offer
    video+audio urls and most sites need headers/cookies that QMediaPlayer
    doesn't send (HTTP 403). yt-dlp already solves all of that for any site.
    Stability is more important than quality here, the download quality is
    selected separated.
    The file extension is not forced: when a site delivers a single file
    (ex.: archive.org .ogv) QMediaPlayer plays it the same way.
"""
class PreviewDownloader:
    """ "-S res:240": largest resolution up to 240p (or the smallest above),
        H.264 + AAC preferred, then the smallest bitrate - it's just a preview.
    """
    FORMAT_SORT = "res:240,vcodec:h264,acodec:aac,+br"

    def __init__(self):
        self.process = None
        self._cancelled = False

    # download the preview, return the local file path or None if it fails
    def download(self, url, out_dir, name):
        base = os.path.join(out_dir, name)
        try:
            command = [
                get_ytdlp_path(), url,
                "--no-playlist", "--no-part", "--no-warnings", "-q",
                "-f", "bv*+ba/b",
                "-S", self.FORMAT_SORT,
                "--merge-output-format", "mp4",
                "--ffmpeg-location", get_ffmpeg_path(),
                "--js-runtimes", f"node:{get_node_path()}",
                # "%%" = literal "%" on yt-dlp output template
                "-o", base.replace("%", "%%") + ".%(ext)s",
            ]
            # same authentication of the real download
            if is_youtube(url):
                command += YOUTUBE_CLIENT_SETTINGS
            if cookies_exists():
                command += ["--cookies", get_cookies_path()]

            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            # output is not read, DEVNULL avoids the process blocking on a full pipe
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self.process.wait()
            ok = self.process.returncode == 0
        except Exception:
            ok = False

        files = [f for f in glob.glob(glob.escape(base) + ".*")
                 if not f.endswith((".part", ".ytdl", ".temp"))]

        if self._cancelled or not ok or not files:
            # nothing useful: remove whatever was left behind
            for f in glob.glob(glob.escape(base) + ".*"):
                try:
                    os.remove(f)
                except OSError:
                    pass
            return None
        return max(files, key=os.path.getctime)

    # stop the download (dialog closed / another link pasted)
    def cancel(self):
        self._cancelled = True
        p = self.process
        if not p or p.poll() is not None:
            return
        try:
            if sys.platform == "win32":
                # kill yt-dlp and its children (ffmpeg merging)
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                p.kill()
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
