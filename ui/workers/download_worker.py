import os
import glob
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal

from core.utils import (
    get_ffmpeg_path,
    get_ffmpeg_exe,
    get_ytdlp_path,
    get_node_path,
    get_cookies_path,
    cookies_exists,
    is_youtube,
    safe_filename,
)


class DownloadWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(object, str)
    cancelled = Signal(object)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.process = None
        self._is_cancelled = False

    def run(self):
        try:
            self.item.status = "downloading"
            self.progress.emit(0)

            safe_title = safe_filename(self.item.title)
            base = os.path.join(self.item.output_path, safe_title)
            for pattern in [f"{base}*.part", f"{base}*.ytdl", f"{base}*.temp", f"{base}*.frag*"]:
                for f in glob.glob(pattern):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

            is_clip = (getattr(self.item, "clip_start", None) is not None
                       or getattr(self.item, "clip_end", None) is not None)

            if is_clip:
                final_path = self._run_clip_strategy()
            else:
                command = self._build_command()
                success = self._run_process(command)

                if not success:
                    if self.item.status == "cancelled":
                        return
                    raise Exception("Falha no download (yt-dlp retornou erro)")

                final_path = self._find_downloaded_file()

            if self._is_cancelled:
                return

            if not final_path or not os.path.exists(final_path):
                raise Exception("Arquivo final não encontrado")

            self.item.file_path = final_path
            self.item.status = "completed"
            self.finished.emit(self.item)

        except Exception as e:
            if self._is_cancelled:
                return
            self.item.status = "error"
            self.error.emit(self.item, str(e))

    # ==========================
    # CLIP: baixar completo + cortar com ffmpeg
    # ==========================
    def _run_clip_strategy(self):
        ffmpeg_exe = get_ffmpeg_exe()
        safe_title = safe_filename(self.item.title)

        tmp_title = f"{safe_title}__full_tmp"
        tmp_template = os.path.join(self.item.output_path, f"{tmp_title}.%(ext)s")

        # Download completo (sem flags de corte)
        command = self._build_command(output_override=tmp_template, for_clip=True)
        success = self._run_process(command)

        if self._is_cancelled:
            self._cleanup_pattern(os.path.join(self.item.output_path, f"{tmp_title}*"))
            return None

        if not success:
            self._cleanup_pattern(os.path.join(self.item.output_path, f"{tmp_title}*"))
            raise Exception("Falha no download do vídeo completo")

        full_files = glob.glob(os.path.join(self.item.output_path, f"{tmp_title}*"))
        full_files = [f for f in full_files if not f.endswith((".part", ".ytdl", ".temp"))]
        if not full_files:
            raise Exception("Arquivo temporário não encontrado")
        full_path = max(full_files, key=os.path.getctime)

        self.progress.emit(99)

        clip_start = getattr(self.item, "clip_start", None)
        clip_end = getattr(self.item, "clip_end", None)

        fmt = (self.item.format_type or "MP4").upper()
        out_ext = ".mp3" if fmt == "MP3" else ".mp4"
        out_path = os.path.join(self.item.output_path, f"{safe_title}{out_ext}")

        if os.path.exists(out_path) and not getattr(self.item, "overwrite", False):
            base_name = safe_title
            i = 1
            while os.path.exists(out_path):
                out_path = os.path.join(self.item.output_path, f"{base_name} ({i}){out_ext}")
                i += 1

        ffmpeg_cmd = [ffmpeg_exe, "-hwaccel", "none", "-y", "-i", full_path]

        if clip_start is not None:
            ffmpeg_cmd += ["-ss", f"{float(clip_start):.3f}"]
        if clip_end is not None:
            ffmpeg_cmd += ["-to", f"{float(clip_end):.3f}"]

        if fmt == "MP3":
            ffmpeg_cmd += ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
        else:
            ffmpeg_cmd += ["-c", "copy"]

        ffmpeg_cmd.append(out_path)

        cut_ok = self._run_ffmpeg(ffmpeg_cmd)

        if not cut_ok and not self._is_cancelled and fmt != "MP3":
            ffmpeg_cmd2 = [ffmpeg_exe, "-hwaccel", "none", "-y", "-i", full_path]
            if clip_start is not None:
                ffmpeg_cmd2 += ["-ss", f"{float(clip_start):.3f}"]
            if clip_end is not None:
                ffmpeg_cmd2 += ["-to", f"{float(clip_end):.3f}"]
            ffmpeg_cmd2 += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast"]
            ffmpeg_cmd2.append(out_path)
            cut_ok = self._run_ffmpeg(ffmpeg_cmd2)

        try:
            os.remove(full_path)
        except Exception:
            pass

        if self._is_cancelled:
            try:
                os.remove(out_path)
            except Exception:
                pass
            return None

        if not cut_ok:
            raise Exception("ffmpeg falhou ao cortar o trecho")

        return out_path

    def _run_ffmpeg(self, cmd):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )

            def _drain():
                try:
                    for _ in self.process.stderr:
                        pass
                except Exception:
                    pass

            threading.Thread(target=_drain, daemon=True).start()

            for _ in self.process.stdout:
                if self._is_cancelled:
                    self._kill_process_tree()
                    return False

            self.process.wait()
            return self.process.returncode == 0
        except Exception:
            return False

    def _cleanup_pattern(self, pattern):
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except Exception:
                pass

    # ==========================
    # BUILD COMMAND - CORRIGIDA
    # ==========================
    def _build_command(self, output_override=None, for_clip=False):
        ffmpeg_path = get_ffmpeg_path()
        ytdlp_path = get_ytdlp_path()
        safe_title = safe_filename(self.item.title)

        if output_override:
            output_template = output_override
        else:
            output_template = os.path.join(self.item.output_path, f"{safe_title}.%(ext)s")

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

        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        node_path = get_node_path()
        if node_path and os.path.exists(node_path):
            command += ["--js-runtime", f"node:{node_path}"]
        else:
            command += ["--js-runtime", "node"]

        if getattr(self.item, "overwrite", False) and not for_clip:
            command += ["--force-overwrites"]

        # MP3
        if self.item.format_type.upper() == "MP3":
            if for_clip:
                command += ["-f", "bestaudio", "--no-keep-video"]
            else:
                command += [
                    "-f", "bestaudio",
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "192K",
                ]
            return command

        # MP4 - SEM o bug do --postprocessor-args
        if self.item.format_type.upper() == "MP4":
            if self.item.quality_id and "+" in self.item.quality_id:
                video_format = self.item.quality_id
            else:
                video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

            if is_youtube(self.item.url):
                command += ["--extractor-args", "youtube:player_client=web_safari,android_vr"]

            command += [
                "-f", video_format,
                "--merge-output-format", "mp4",
                "--no-mtime",
                "--no-continue",
            ]

            return command

        return command

    # ==========================
    # PROCESS
    # ==========================
    def _run_process(self, command):
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )

        def _drain_stderr():
            try:
                for _ in self.process.stderr:
                    pass
            except Exception:
                pass

        threading.Thread(target=_drain_stderr, daemon=True).start()

        last_emitted = -1
        merge_started = False

        for line in self.process.stdout:
            if self._is_cancelled:
                break
            if not line:
                continue
            line = line.strip()

            if "Merging formats" in line or "[ffmpeg]" in line:
                merge_started = True
                continue

            if "[download]" in line and "%" in line:
                try:
                    percent = float(line.split("%")[0].split()[-1])
                    if merge_started:
                        continue
                    p = min(99, int(percent))
                    if p > last_emitted:
                        last_emitted = p
                        self.progress.emit(p)
                except Exception:
                    pass

        if self._is_cancelled:
            self._kill_process_tree()
            try:
                self.process.wait(timeout=5)
            except Exception:
                pass
            self.item.status = "cancelled"
            self.cancelled.emit(self.item)
            return False

        self.process.wait()
        self.progress.emit(100)
        return self.process.returncode == 0

    # ==========================
    # CANCEL
    # ==========================
    def cancel(self):
        self._is_cancelled = True
        self._kill_process_tree()

    def _kill_process_tree(self):
        p = self.process
        if not p:
            return
        try:
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
            else:
                p.kill()
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    def _find_downloaded_file(self):
        try:
            safe_title = safe_filename(self.item.title)
            pattern = os.path.join(self.item.output_path, f"{safe_title}*")
            files = [f for f in glob.glob(pattern)
                     if not f.endswith((".part", ".ytdl", ".temp"))
                     and "__full_tmp" not in f]
            if not files:
                return ""
            return max(files, key=os.path.getctime)
        except Exception as e:
            print("Erro ao localizar arquivo:", e)
            return ""