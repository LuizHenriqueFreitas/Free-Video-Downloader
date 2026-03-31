import os
import glob
import re
import subprocess

from PySide6.QtCore import QObject, Signal

from core.utils import (
    get_ffmpeg_path,
    get_ytdlp_path,
    get_node_path,
    get_cookies_path,
    cookies_exists
)


def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name)


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

    # ==========================
    # MAIN
    # ==========================
    def run(self):
        try:
            print(f"\n🚀 Iniciando download: {self.item.title}")

            self.item.status = "downloading"

            command = self._build_command()

            success = self._run_process(command)

            if not success:
                raise Exception("Falha no download (yt-dlp retornou erro)")

            final_path = self._find_downloaded_file()

            if not final_path:
                raise Exception("Arquivo final não encontrado")

            self.item.file_path = final_path
            self.item.status = "completed"

            print("✅ Download finalizado:", final_path)

            self.finished.emit(self.item)

        except Exception as e:
            print("❌ ERRO WORKER:", e)
            self.item.status = "error"
            self.error.emit(self.item, str(e))

    # ==========================
    # BUILD COMMAND
    # ==========================
    def _build_command(self):
        ffmpeg_path = get_ffmpeg_path()
        ytdlp_path = get_ytdlp_path()

        safe_title = safe_filename(self.item.title)

        output_template = os.path.join(
            self.item.output_path,
            f"{safe_title}.%(ext)s"
        )

        # 🎯 QUALIDADE REAL (SEM LIMITAR EXTENSÃO)
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
            "--user-agent", "Mozilla/5.0",
            "--extractor-args", "youtube:player_client=web",
            "--js-runtimes", f"node:{get_node_path()}",
            "-f", video_format,
]

        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # 🎬 saída final
        if self.item.format_type == "MP4":
            command += [
                "--merge-output-format", "mp4"
            ]

        elif self.item.format_type == "MP3":
            command += [
                "-f", "bestaudio",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
            ]

        return command

    # ==========================
    # PROCESS
    # ==========================
    def _run_process(self, command):
        print("\n📦 COMANDO EXECUTADO:")
        print(" ".join(command), "\n")

        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in self.process.stdout:
            if not line:
                continue

            line = line.strip()
            print(line)

            # cancelamento
            if self._is_cancelled:
                print("⚠️ Cancelando download...")
                self.process.kill()
                self.item.status = "cancelled"
                self.cancelled.emit(self.item)
                return False

            # progresso
            if "[download]" in line and "%" in line:
                try:
                    percent = float(line.split("%")[0].split()[-1])
                    self.progress.emit(int(percent))
                except:
                    pass

        self.process.wait()

        return self.process.returncode == 0

    # ==========================
    # CANCEL
    # ==========================
    def cancel(self):
        self._is_cancelled = True

        if self.process:
            try:
                self.process.kill()
            except:
                pass

    # ==========================
    # FILE FINDER CORRETO
    # ==========================
    def _find_downloaded_file(self):
        try:
            safe_title = safe_filename(self.item.title)

            pattern = os.path.join(
                self.item.output_path,
                f"{safe_title}*"
            )

            files = glob.glob(pattern)

            if not files:
                return ""

            # pega o mais recente
            return max(files, key=os.path.getctime)

        except Exception as e:
            print("Erro ao localizar arquivo:", e)
            return ""