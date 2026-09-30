# ui/workers/download_worker.py

""" Here you will find (more relevant metods):
    - run_download() function;
    - build_download_command;
    - _run_ytdlp thread function;
    - _run_ffmepg thread function (with conversion progress);
    - _run_clip alternative download;
    - _ensure_mp4_h264 final file conversion;
    - _kill process fallbacks;
    - _find_file_path;

    About Logic implemented
        Download_builder function and Clip_strategy function
        both implement ytdlp and ffmpeg separatly, like
        util/video_info.py too.

        Maybe in next versions is a good ideia refatorate this
        and move some of this file functions to another file.
"""

import os
import re
import glob
import json
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal

from core.i18n import tr
from core.utils import (
    get_ffmpeg_path,
    get_ffmpeg_exe,
    get_ffprobe_exe,
    get_ytdlp_path,
    get_node_path,
    get_cookies_path,
    cookies_exists,
    is_youtube,
    safe_filename,
    get_h264_video_args,
    CPU_H264_ARGS,
    YOUTUBE_CLIENT_SETTINGS
)

""" Original audio track only. Some youtube videos have dubbed audio tracks
    (other languages); yt-dlp gives the original one the highest
    "language_preference" (10, dubbed ones -1), and "lang" sorts by it.
    It must be the 1st field: fields given with "-S" go before yt-dlp's
    defaults, so "acodec:aac" alone could pick an AAC dub over an Opus-only
    original. Videos with a single track are not affected.
"""
AUDIO_FORMAT_SORT = "lang"

""" yt-dlp format sort for MP4: original audio (see above), then the highest
    resolution allowed by "-f", then H.264 video and AAC audio when they exist
    on that resolution. Without that yt-dlp prefers AV1/VP9 + Opus, that many
    players/editors can't open (v1.0.0 promise: MP4 with H.264 + AAC).
"""
MP4_FORMAT_SORT = f"{AUDIO_FORMAT_SORT},res,vcodec:h264,acodec:aac"

""" Decode the source video on GPU when re-encoding ("-hwaccel auto").
    ffmpeg falls back to CPU decoding by itself when there's no GPU support.
    On Linux + AMD (VAAPI) GPU decoding was slower than CPU decoding, so if
    that also happens on Windows, just turn it off here.
"""
USE_HW_DECODE = True


""" ===========================
    AUDIO LANGUAGE (dubbed videos)
    (pure functions - easy to test)
  =========================== """

# yt-dlp language codes: "pt", "en-US", "es-419", "zh-Hans"...
# anything else is ignored, it goes inside the "-f" expression
_LANGUAGE_CODE = re.compile(r"^[A-Za-z0-9-]+$")

def _valid_language(language):
    return bool(language) and bool(_LANGUAGE_CODE.match(language))

""" MP4 format with the audio track of the chosen language.
    Each "video+bestaudio" alternative is repeated first with
    "bestaudio[language=xx]"; the original alternatives stay after them, so if
    that language isn't available anymore yt-dlp downloads the original track
    (AUDIO_FORMAT_SORT) instead of failing.
    "bestvideo[height<=720]+bestaudio/best[height<=720]", "pt" ->
    "bestvideo[height<=720]+bestaudio[language=pt]/bestvideo[height<=720]+bestaudio/best[height<=720]"
"""
def with_audio_language(video_format, language):
    if not _valid_language(language):
        return video_format
    alternatives = video_format.split("/")
    chosen = [
        re.sub(r"\+bestaudio((?:\[[^\]]*\])*)",
               lambda m: f"+bestaudio{m.group(1)}[language={language}]", alt)
        for alt in alternatives if "+bestaudio" in alt
    ]
    return "/".join(chosen + alternatives)

# MP3 format: the chosen language, or the original track if it doesn't exist
def audio_format(language):
    if not _valid_language(language):
        return "bestaudio"
    return f"bestaudio[language={language}]/bestaudio"


""" ===========================
    FFMPEG PROGRESS HELPERS
    (pure functions - easy to test)
  =========================== """

# parse one "-progress" line from ffmpeg: "out_time_us=12500000" -> ("out_time_us", "12500000")
def _parse_progress_line(line):
    if not line or "=" not in line:
        return None
    key, _, value = line.strip().partition("=")
    return key.strip(), value.strip()

# estimated seconds left, or None while the estimate isn't reliable yet
# (the first seconds / percents of a conversion are very inaccurate)
def _estimate_remaining(elapsed, fraction):
    if elapsed < 3 or fraction < 0.02:
        return None
    return elapsed * (1 - fraction) / fraction


# main class from this file
class DownloadWorker(QObject):
    progress = Signal(int)
    # (kind, percent, seconds left) - kind: "convert" or "cut",
    # percent -1 = unknown duration, seconds -1 = still calculating
    conversion_progress = Signal(str, int, int)
    finished = Signal(object)
    error = Signal(object, str)
    cancelled = Signal(object)

    def __init__(self, item):
        super().__init__()
        # this "item" came from models/download_item.py
        self.item = item
        self.process = None
        self._is_cancelled = False
        self._last_stderr = ""
        # cancelled signal must be emitted only once per download: each emit
        # frees a slot at DownloadService queue (running -= 1)
        self._cancel_emitted = False


    """ ======================
        RUN DOWNLOAD FUNCTION
      ====================== """
    # main class function, manage all download configuration
    def run_download(self):
        # check if the donwload was cancelled
        if self._is_cancelled:
            self._emit_cancelled()
            return

        try:
            self.item.status = "downloading"
            self.progress.emit(0)

            # below checking if file is unique on the outpot path
            # glob.escape(): titles may have "[", "]", "*" or "?" (ex.: "[Official Video]"),
            # which glob understands as patterns, not as text - so the file is never found
            safe_title = safe_filename(self.item.title)
            base = glob.escape(os.path.join(self.item.output_path, safe_title))
            for pattern in [f"{base}*.part", f"{base}*.ytdl", f"{base}*.temp",
                            f"{base}*.frag*", f"{base}*.__converting.mp4"]:
                for f in glob.glob(pattern):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

            # check if it's a clip from a entire video
            is_clip = (getattr(self.item, "clip_start", None) is not None
                       or getattr(self.item, "clip_end", None) is not None)

            # if it's a clip, call the specific function
            if is_clip:
                final_path = self._run_clip_strategy()
            # if isn't a clip, build download command line and run process
            else:
                command = self._build_download_command()
                success = self._run_ytdlp_process(command)

                if not success:
                    # cancelled: the "cancelled" signal was already emitted
                    if self._is_cancelled or self.item.status == "cancelled":
                        return
                    detail = self._last_stderr.splitlines()[-1] if self._last_stderr else ""
                    message = (tr("worker.ytdlp_failed_detail", detail=detail) if detail
                               else tr("worker.ytdlp_failed"))
                    raise Exception(message)

                # without ffmpeg yt-dlp doesn't merge and leaves 2 files
                self._check_merge_leftovers()

                final_path = self._find_downloaded_file()

                # every video file delivered must be .mp4 H.264 + AAC
                if final_path and (self.item.format_type or "MP4").upper() == "MP4":
                    final_path = self._ensure_mp4_h264(final_path)

            # if cancelled, skip reminder code
            if self._is_cancelled:
                self._emit_cancelled()
                return

            # check file path
            if not final_path or not os.path.exists(final_path):
                raise Exception(tr("worker.final_file_not_found"))

            # finish run process
            self.item.file_path = final_path
            self.item.status = "completed"
            self.finished.emit(self.item)

        # Exception sender if there's an error ocurred
        except Exception as e:
            if self._is_cancelled:
                self._emit_cancelled()
                return
            self.item.status = "error"
            self.error.emit(self.item, str(e))

    # emit "cancelled" just once, even if more than one step notices the cancel
    def _emit_cancelled(self):
        if self._cancel_emitted:
            return
        self._cancel_emitted = True
        self.item.status = "cancelled"
        self.cancelled.emit(self.item)


    """ ==========================
        TRIMMER TOOL OPTIONS
       ========================= """

    """ Maybe could that be changed to another file, just to that function
        because has a lot o code on this file, and that is a very different function.
    """

    # if is a clip, need to use that function
    def _run_clip_strategy(self):
        # get necessary resources
        ffmpeg_exe = get_ffmpeg_exe()
        safe_title = safe_filename(self.item.title)

        """ The clip download logic is that:
            - First download the entire clip, so you will need to have all the
            clip size on your disk.
            - After downloaded the app will use ffmpeg to cut the file to the clip.
            - And after this the complete file will be deleted.
            - At the final you will have just the clip part you select.

            That was decided because is a stable and simple option.
        """
        tmp_title = f"{safe_title}__full_tmp"
        # "%" is special on yt-dlp output template (ex.: %(ext)s),
        # "%%" writes a literal "%" in the final file name
        tmp_template = os.path.join(self.item.output_path, tmp_title).replace("%", "%%") + ".%(ext)s"
        tmp_pattern = glob.escape(os.path.join(self.item.output_path, tmp_title)) + "*"

        # call commandline builder and start download process
        command = self._build_download_command(output_override=tmp_template, for_clip=True)
        success = self._run_ytdlp_process(command)

        # if canceled checker
        if self._is_cancelled:
            self._cleanup_pattern(tmp_pattern)
            return None

        # if error checker
        if not success:
            self._cleanup_pattern(tmp_pattern)
            detail = self._last_stderr.splitlines()[-1] if self._last_stderr else ""
            message = (tr("worker.full_video_failed_detail", detail=detail) if detail
                       else tr("worker.full_video_failed"))
            raise Exception(message)

        # temporary full file verification
        full_files = glob.glob(tmp_pattern)
        full_files = [f for f in full_files if not f.endswith((".part", ".ytdl", ".temp"))]
        # if temp file was not found return an error
        if not full_files:
            raise Exception(tr("worker.temp_file_not_found"))
        full_path = max(full_files, key=os.path.getctime)

        # emit UI progress information
        self.progress.emit(99)

        """ From here we already has the temp full video localy
            we'll just extract the wished clip using ffmepg operations.
        """
        # get start and end clip time stamps
        clip_start = getattr(self.item, "clip_start", None)
        clip_end = getattr(self.item, "clip_end", None)

        # get clip format (extension, like .mp4 or .mp3) and output path
        fmt = (self.item.format_type or "MP4").upper()
        out_ext = ".mp3" if fmt == "MP3" else ".mp4"
        out_path = os.path.join(self.item.output_path, f"{safe_title}{out_ext}")

        # if path exists and is not to overwrite older file with same name
        # increment "(x)", where x is a number at the end of file name
        if os.path.exists(out_path) and not getattr(self.item, "overwrite", False):
            base_name = safe_title
            i = 1
            while os.path.exists(out_path):
                out_path = os.path.join(self.item.output_path, f"{base_name} ({i}){out_ext}")
                i += 1

        # clip length, used by the progress bar (None = unknown)
        start = float(clip_start or 0)
        if clip_end is not None:
            total = float(clip_end) - start
        else:
            full_duration = self._probe_media(full_path, required=False).get("duration")
            total = full_duration - start if full_duration else None

        """ Always re-encode the clip: with "-c copy" the video can only start on a
            keyframe (every ~2-5s on youtube), so the video starts some seconds after
            the audio (frozen/black image at clip start).
            "-ss" before "-i" = fast and accurate seek when re-encoding.
            "-t" (duration) instead of "-to": with "-ss" before "-i" the output
            timestamps restart at 0, so "-to" would be wrong.
        """
        def build_cut_command(video_args):
            cmd = [ffmpeg_exe, "-y"]
            # GPU decoding only when re-encoding video (see USE_HW_DECODE)
            if fmt != "MP3" and USE_HW_DECODE and video_args != CPU_H264_ARGS:
                cmd += ["-hwaccel", "auto"]
            if clip_start is not None:
                cmd += ["-ss", f"{start:.3f}"]
            cmd += ["-i", full_path]
            if clip_end is not None:
                cmd += ["-t", f"{float(clip_end) - start:.3f}"]

            if fmt == "MP3":
                cmd += ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
            else:
                # H.264 (GPU when available) + AAC: same codecs of normal downloads
                cmd += ["-map", "0:v:0?", "-map", "0:a:0?"]
                cmd += video_args
                cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]

            # "-progress pipe:1" writes the progress on stdout (see _run_ffmpeg)
            cmd += ["-progress", "pipe:1", "-nostats", out_path]
            return cmd

        video_args = get_h264_video_args() if fmt != "MP3" else CPU_H264_ARGS
        cut_ok = self._run_ffmpeg(build_cut_command(video_args), "cut", total)

        # GPU encoder failed on this file (ex.: too many GPU sessions at once):
        # try again using CPU, the user just see the progress bar restarting
        if not cut_ok and not self._is_cancelled and video_args != CPU_H264_ARGS:
            self._remove_file(out_path)
            cut_ok = self._run_ffmpeg(build_cut_command(CPU_H264_ARGS), "cut", total)

        # remove temporary resources
        self._remove_file(full_path)

        # if was canceld, remove temporary resouces in use
        if self._is_cancelled:
            self._remove_file(out_path)
            return None

        if not cut_ok:
            self._remove_file(out_path)
            raise Exception(tr("worker.cut_failed"))

        # final response is the final file path
        return out_path


    """ ==========================
        FINAL FILE FORMAT (.mp4 H.264)
      ========================== """

    """ Every video file delivered by Get Media Free must be .mp4 with
        H.264 video + AAC audio (compatible with any player/editor).
        YouTube up to 1080p already comes like that (see MP4_FORMAT_SORT),
        but 1440p/4K (only VP9/AV1 exists) and other sites (ex.: .webm, .ogv)
        need conversion.
        Only what is needed is converted: H.264 video is copied, not re-encoded.
        Return the final .mp4 path, or None if cancelled.
    """
    def _ensure_mp4_h264(self, path):
        info = self._probe_media(path)
        ext = os.path.splitext(path)[1].lower()
        video_ok = info.get("vcodec") in (None, "h264")
        audio_ok = info.get("acodec") in (None, "aac")

        # most common case (youtube up to 1080p): nothing to do
        if ext == ".mp4" and video_ok and audio_ok:
            return path

        root = os.path.splitext(path)[0]
        final_path = root + ".mp4"
        # temporary output: the source can be a .mp4 too (ex.: VP9 inside .mp4)
        tmp_path = root + ".__converting.mp4"

        def build_convert_command(video_args):
            cmd = [get_ffmpeg_exe(), "-y"]
            # GPU decoding only when re-encoding video (see USE_HW_DECODE)
            if not video_ok and USE_HW_DECODE and video_args != CPU_H264_ARGS:
                cmd += ["-hwaccel", "auto"]
            cmd += ["-i", path]
            # first video and audio tracks only (subtitles/data don't fit .mp4)
            cmd += ["-map", "0:v:0?", "-map", "0:a:0?"]
            cmd += ["-c:v", "copy"] if video_ok else video_args
            cmd += ["-c:a", "copy"] if audio_ok else ["-c:a", "aac", "-b:a", "192k"]
            # "-progress pipe:1" writes the progress on stdout (see _run_ffmpeg)
            cmd += ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", tmp_path]
            return cmd

        video_args = CPU_H264_ARGS if video_ok else get_h264_video_args()
        ok = self._run_ffmpeg(build_convert_command(video_args), "convert", info.get("duration"))

        # GPU encoder failed on this file: try again using CPU
        if not ok and not self._is_cancelled and video_args != CPU_H264_ARGS:
            self._remove_file(tmp_path)
            ok = self._run_ffmpeg(build_convert_command(CPU_H264_ARGS), "convert", info.get("duration"))

        if self._is_cancelled:
            self._remove_file(tmp_path)
            return None

        if not ok:
            self._remove_file(tmp_path)
            raise Exception(tr("worker.convert_failed"))

        # replace the source by the converted file
        os.replace(tmp_path, final_path)
        if os.path.normcase(path) != os.path.normcase(final_path):
            self._remove_file(path)
        return final_path

    # read first video/audio codec and duration with ffprobe
    # returns {"vcodec": str|None, "acodec": str|None, "duration": float|None}
    def _probe_media(self, path, required=True):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        info = {"vcodec": None, "acodec": None, "duration": None}
        try:
            result = subprocess.run(
                [get_ffprobe_exe(), "-v", "error",
                 "-show_entries", "stream=codec_type,codec_name:format=duration",
                 "-of", "json", path],
                capture_output=True, text=True, timeout=60,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            if result.returncode != 0:
                raise Exception(result.stderr.strip())
            data = json.loads(result.stdout or "{}")
        except Exception:
            if required:
                raise Exception(tr("worker.probe_failed"))
            return info

        for stream in data.get("streams", []):
            kind = stream.get("codec_type")
            if kind == "video" and info["vcodec"] is None:
                info["vcodec"] = stream.get("codec_name")
            elif kind == "audio" and info["acodec"] is None:
                info["acodec"] = stream.get("codec_name")
        try:
            info["duration"] = float(data.get("format", {}).get("duration"))
        except (TypeError, ValueError):
            info["duration"] = None
        return info


    """ ==========================
        FFMPEG PROCESS
      ========================== """

    """ ffmpeg internal process function.
        kind: "convert" / "cut" - when given, the progress written by
        "-progress pipe:1" is read and sent to the UI (conversion_progress)
        with the estimated time left. total_seconds is the output duration.
    """
    def _run_ffmpeg(self, cmd, kind=None, total_seconds=None):
        # windows controller to avoid prompt windows
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        # try to run ffmpeg on separete thread
        try:
            # configurating subprocess
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )

            # ffmpeg writes a lot on stderr, it must be read or the process blocks
            stderr_lines = []
            def _drain():
                try:
                    for line in self.process.stderr:
                        stderr_lines.append(line)
                        # keep just the last lines (error message)
                        del stderr_lines[:-50]
                except Exception:
                    pass

            # start a separete thread, how it is daemon, if the function end the thread is turned off
            threading.Thread(target=_drain, daemon=True).start()

            # progress state
            start = time.monotonic()
            last_emit = 0.0
            out_time = 0.0
            shown_eta = None
            total = float(total_seconds) if total_seconds and total_seconds > 0 else None

            # first feedback: bar in conversion mode, still calculating
            if kind:
                self.conversion_progress.emit(kind, 0 if total else -1, -1)

            # check output - kill process tree is there's an error
            for raw in self.process.stdout:
                if self._is_cancelled:
                    self._kill_process_tree()
                    self._emit_cancelled()
                    return False
                if not kind:
                    continue

                parsed = _parse_progress_line(raw.decode("utf-8", errors="replace"))
                if not parsed:
                    continue
                key, value = parsed

                # microseconds of the output already processed
                if key == "out_time_us":
                    try:
                        out_time = int(value) / 1_000_000
                    except ValueError:
                        pass
                # "progress" closes each block - update UI at most once per second
                elif key == "progress":
                    now = time.monotonic()
                    if value != "end" and now - last_emit < 1:
                        continue
                    last_emit = now
                    if not total:
                        self.conversion_progress.emit(kind, -1, -1)
                        continue
                    fraction = max(0.0, min(out_time / total, 1.0))
                    eta = _estimate_remaining(now - start, fraction)
                    if eta is not None:
                        # smooth the estimate to avoid jumps (5min -> 2min -> 6min)
                        shown_eta = eta if shown_eta is None else 0.3 * eta + 0.7 * shown_eta
                    seconds_left = int(shown_eta) if shown_eta is not None else -1
                    self.conversion_progress.emit(kind, int(fraction * 100), seconds_left)

            # subprocess finishing
            self.process.wait()
            if self._is_cancelled:
                self._emit_cancelled()
                return False
            self._last_stderr = b"".join(stderr_lines).decode("utf-8", errors="replace").strip()
            return self.process.returncode == 0

        # return error if bad request tring ffmpeg command
        except Exception:
            return False

    # cleaning internal function - called on error sections
    def _cleanup_pattern(self, pattern):
        for f in glob.glob(pattern):
            self._remove_file(f)

    # remove a file ignoring errors (file already removed, in use, etc.)
    @staticmethod
    def _remove_file(path):
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


    """ =========================
        DOWNLOAD BUILD COMMAND
     ========================== """

    # this function is the download command line constructor
    def _build_download_command(self, output_override=None, for_clip=False):
        # get resouces from utils
        ffmpeg_path = get_ffmpeg_path()
        ytdlp_path = get_ytdlp_path()
        safe_title = safe_filename(self.item.title)

        # check if allow overwrite or need to increment name
        if output_override:
            output_template = output_override
        else:
            # "%" is special on yt-dlp output template (ex.: %(ext)s),
            # "%%" writes a literal "%" in the final file name
            output_template = os.path.join(self.item.output_path, safe_title).replace("%", "%%") + ".%(ext)s"

        # start build yt-dlp command line
        command = [
            ytdlp_path,
            self.item.url,
            "-o", output_template,
            "--ffmpeg-location", ffmpeg_path,
            "--no-playlist",
            "--no-part",
            "--no-check-certificates",
            "--newline",
        ]

        # check cookies
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # get node
        node_path = get_node_path()
        if node_path and os.path.exists(node_path):
            command += ["--js-runtimes", f"node:{node_path}"]
        else:
            command += ["--js-runtimes", "node"]

        # if is the case, set overwrite file mode
        if getattr(self.item, "overwrite", False) and not for_clip:
            command += ["--force-overwrites"]

        # set yt-dlp youtube data client (can be an empty list, see utils.py)
        if is_youtube(self.item.url):
            command += YOUTUBE_CLIENT_SETTINGS

        # audio track language chosen by the user (None = original track)
        language = getattr(self.item, "audio_language", None)

        # MP3 download command line
        if self.item.format_type.upper() == "MP3":
            if for_clip:
                # if is a media clip donwload
                command += ["-f", audio_format(language), "-S", AUDIO_FORMAT_SORT, "--no-keep-video"]
            else:
                # if is a full media audio download
                command += [
                    "-f", audio_format(language),
                    "-S", AUDIO_FORMAT_SORT,
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "192K",
                ]
            return command

        # MP4 download command line
        if self.item.format_type.upper() == "MP4":
            # set quality selected
            if self.item.quality_id and "+" in self.item.quality_id:
                # manual selected quality
                video_format = self.item.quality_id
            else:
                # auto best quality
                video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            # audio track chosen on the audio language dialog (None = original)
            video_format = with_audio_language(video_format, language)

            # ends yt-dlp command line
            command += [
                "-f", video_format,
                # original audio, then H.264 + AAC without lowering the resolution (see MP4_FORMAT_SORT)
                "-S", MP4_FORMAT_SORT,
                "--merge-output-format", "mp4",
                "--no-mtime",
                "--no-continue",
            ]

            return command

        return command


    """ ====================
            RUN PROCESS
      ==================="""

    def _run_ytdlp_process(self, command):
        # windows controller to avoid prompt windows
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        # configurating subprocess
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        # ytdlp execution function
        stderr_lines = []
        def _drain_stderr():
            try:
                for line in self.process.stderr:
                    stderr_lines.append(line)
            except Exception:
                pass

        # start a separete thread, how it is daemon, if the function end the thread is turned off
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # process management
        last_emitted = -1
        merge_started = False

        # check process output
        for line in self.process.stdout:
            # check if was cancelled
            if self._is_cancelled:
                break
            # continue if there's no line
            if not line:
                continue
            # treat line to checkout
            line = line.strip()

            # recognizes whe entry to merging video and audio to same file
            if "Merging formats" in line or "[ffmpeg]" in line:
                merge_started = True
                continue

            # a new "Destination:" line means yt-dlp started a new stream
            # (ex.: video finished, now downloading audio) - percent restarts
            # from 0%, so the high-water mark needs to reset too, otherwise
            # the bar gets stuck at the previous stream's last percent
            if "[download] Destination:" in line:
                last_emitted = -1
                continue

            # get the download '%' to be used on interface
            if "[download]" in line and "%" in line:
                try:
                    percent = float(line.split("%")[0].split()[-1])
                    # if merge state just cotinue because will be paused at 99%
                    if merge_started:
                        continue
                    p = min(99, int(percent))
                    # updates always p was updated
                    if p > last_emitted:
                        last_emitted = p
                        self.progress.emit(p)
                except Exception:
                    pass

        # if it was cancelled - kill all involved process
        if self._is_cancelled:
            self._kill_process_tree()
            try:
                self.process.wait(timeout=5)
            except Exception:
                pass
            self._emit_cancelled()
            return False

        # finishing process
        self.process.wait()
        stderr_thread.join(timeout=5)
        self._last_stderr = "".join(stderr_lines).strip()
        # when merging is concluded emit 100%
        self.progress.emit(100)
        return self.process.returncode == 0


    """ ==========================
            CANCEL PROCESS
      ======================= """

    # cancel function
    def cancel(self):
        # turn _is_cancelled true
        self._is_cancelled = True
        # kill all involved process
        self._kill_process_tree()

    # kill process functions
    def _kill_process_tree(self):
        p = self.process
        # fallback if there's no process
        if not p:
            return
        # try to kill process
        try:
            # for windows OS
            if sys.platform == "win32":
                pid = getattr(p, "pid", None)
                if pid is not None:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    p.kill()
            # for linux
            else:
                p.kill()
        # if doens't work, send an error message
        except Exception:
            # try another time
            try:
                p.kill()
            # send error
            except Exception:
                pass


    """ ========================
            FILE FINDER
      ======================= """

    """ yt-dlp names the separated streams as "title.f<id>.<ext>" and deletes
        them after merging - if they still exist, the merge didn't happen
        (ffmpeg missing or broken) and the user would get 2 files.
    """
    def _check_merge_leftovers(self):
        safe_title = safe_filename(self.item.title)
        base = os.path.join(self.item.output_path, safe_title)
        leftovers = [
            f for f in glob.glob(glob.escape(base) + ".f*.*")
            if re.match(r"^\.f\d[\w-]*\.\w+$", f[len(base):])
        ]
        if leftovers:
            raise Exception(tr("worker.merge_failed"))

    # this function get the system file path
    def _find_downloaded_file(self):
        # try to find the path - very similar in some function above
        try:
            safe_title = safe_filename(self.item.title)
            # glob.escape(): see run_download()
            pattern = glob.escape(os.path.join(self.item.output_path, safe_title)) + "*"
            files = [f for f in glob.glob(pattern)
                     if not f.endswith((".part", ".ytdl", ".temp"))
                     and "__full_tmp" not in f
                     and "__converting" not in f]
            if not files:
                return ""
            return max(files, key=os.path.getctime)
        # bad requesto on try returns empty -> ""
        except Exception as e:
            # is just a console debug message
            print("Failed to locate the downloaded file:", e)
            return ""
