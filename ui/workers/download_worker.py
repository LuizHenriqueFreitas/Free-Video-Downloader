import os
import subprocess

from PySide6.QtCore import QObject, Signal

from core.utils import get_ffmpeg_path, get_ytdlp_path


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

            ffmpeg_path = get_ffmpeg_path()
            ytdlp_path = get_ytdlp_path()

            output_template = os.path.join(
                self.item.output_path,
                f"{self.item.title}.%(ext)s"
            )

            # qualidade
            if self.item.quality == "Full HD":
                video_format = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            else:
                video_format = "bestvideo+bestaudio/best"

            command = [
                ytdlp_path,
                self.item.url,
                "-o", output_template,
                "--ffmpeg-location", ffmpeg_path,
                "--no-playlist",
            ]

            if self.item.format_type == "MP4":
                command += [
                    "-f", video_format,
                    "--merge-output-format", "mp4",
                    "--postprocessor-args", "ffmpeg:-c:v copy -c:a aac -b:a 192k",
                ]
            elif self.item.format_type == "MP3":
                command += [
                    "-f", "bestaudio",
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "192K",
                ]

            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
            )

            last_percent = 0

            for line in self.process.stdout:
                if self._is_cancelled:
                    self.process.kill()
                    self.item.status = "cancelled"
                    self.cancelled.emit(self.item)
                    return

                if "[download]" in line and "%" in line:
                    try:
                        percent_str = line.split("%")[0].split()[-1]
                        percent = int(float(percent_str))

                        if percent != last_percent:
                            last_percent = percent
                            self.progress.emit(percent)

                    except:
                        pass

            self.process.wait()

            if self._is_cancelled:
                return

            if self.process.returncode != 0:
                raise Exception("yt-dlp falhou:\n" + (self.process.stdout.read() or ""))

            # caminho final (mais confiável)
            final_path = self._build_final_path()

            self.item.file_path = final_path
            self.item.status = "completed"

            self.finished.emit(self.item)

        except Exception as e:
            self.item.status = "error"
            self.error.emit(self.item, str(e))

        finally:
            if self.process:
                try:
                    self.process.kill()
                except:
                    pass

    def cancel(self):
        self._is_cancelled = True

        if self.process:
            try:
                self.process.kill()
            except:
                pass

    def _build_final_path(self):
        ext = "mp4" if self.item.format_type == "MP4" else "mp3"
        return os.path.join(self.item.output_path, f"{self.item.title}.{ext}")