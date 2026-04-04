import os
import glob
import re
import subprocess
import sys

from PySide6.QtCore import QObject, Signal

from core.utils import (
    get_ffmpeg_path,
    get_ytdlp_path,
    get_node_path,
    get_cookies_path,
    cookies_exists
)


def safe_filename(name: str) -> str:
    """Remove caracteres inválidos para filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def has_audio(file_path: str, ffmpeg_path: str) -> bool:
    """Checa se o arquivo possui stream de áudio de forma confiável."""
    cmd = [
        ffmpeg_path or "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() == "audio"
    except Exception:
        return False


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

            # Limpa arquivos residuais do yt-dlp
            safe_title = safe_filename(self.item.title)
            base = os.path.join(self.item.output_path, safe_title)
            patterns = [f"{base}*.part", f"{base}*.ytdl", f"{base}*.temp", f"{base}*.frag*"]
            for pattern in patterns:
                for f in glob.glob(pattern):
                    try:
                        os.remove(f)
                        print(f"🗑️ Removido: {f}")
                    except Exception as e:
                        print(f"⚠️ Erro ao remover {f}: {e}")

            # Construir comando e executar
            command = self._build_command()
            success = self._run_process(command)

            if not success:
                if self.item.status == "cancelled":
                    print("✅ Download cancelado pelo usuário.")
                    return
                raise Exception("Falha no download (yt-dlp retornou erro)")

            final_path = self._find_downloaded_file()
            if not final_path or not os.path.exists(final_path):
                raise Exception("Arquivo final não encontrado")

            if self.item.format_type.upper() == "MP4":
                print("🔊 MP4 gerado com áudio (confiando no comando yt-dlp)")

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
        output_template = os.path.join(self.item.output_path, f"{safe_title}.%(ext)s")

        command = [
            ytdlp_path,
            self.item.url,
            "-o", output_template,
            "--ffmpeg-location", ffmpeg_path,
            "--no-playlist",
            "--no-part",
            "--no-check-certificates",
        ]

        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        node_path = get_node_path()
        if node_path and os.path.exists(node_path):
            command += ["--js-runtime", f"node:{node_path}"]
        else:
            command += ["--js-runtime", "node"]

        # MP3
        if self.item.format_type.upper() == "MP3":
            command += [
                "-f", "bestaudio",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
            ]
            return command

        # MP4
        if self.item.format_type.upper() == "MP4":
            # Valida o quality_id: se for algo como "1080p" (texto), não funciona.
            # Nesse caso, usa fallback.
            if self.item.quality_id and "+" in self.item.quality_id:
                video_format = self.item.quality_id
            else:
                video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

            command += [
                "--extractor-args", "youtube:player_client=web_safari,android_vr",
                "-f", video_format,
                "--merge-output-format", "mp4",
                "--postprocessor-args", "ffmpeg:-c:v copy -c:a aac",
                "--no-mtime",
                "--no-continue",
            ]
            return command

        return command

    # ==========================
    # PROCESS
    # ==========================
    def _run_process(self, command):
        print("\n📦 COMANDO EXECUTADO:")
        print(" ".join(command), "\n")

        # 🔥 Configuração para ocultar janela do console no Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW  # 0x08000000

        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,   # <-- adicionado
        )

        last_percent = 0
        merge_started = False
        final_emitted = False

        for line in self.process.stdout:
            if not line:
                continue
            line = line.strip()
            print(line)

            if self._is_cancelled:
                print("⚠️ Cancelando download...")
                self.process.kill()
                self.item.status = "cancelled"
                self.cancelled.emit(self.item)
                return False

            if "Merging formats" in line:
                merge_started = True
                continue

            if "[download]" in line and "%" in line:
                try:
                    percent_str = line.split("%")[0].split()[-1]
                    percent = float(percent_str)

                    if merge_started:
                        continue
                    # Só emite se for maior que o último e < 100
                    if percent > last_percent and percent < 100:
                        last_percent = percent
                        self.progress.emit(int(percent))
                except:
                    pass

        self.process.wait()
        # Emite 100% apenas uma vez no final
        if not final_emitted:
            self.progress.emit(100)
            final_emitted = True

        return self.process.returncode == 0

    # ==========================
    # CANCEL
    # ==========================
    def cancel(self):
        self._is_cancelled = True
        if self.process:
            try:
                self.process.kill()
            except Exception as e:
                print("Erro ao cancelar:", e)

    # ==========================
    # FILE FINDER
    # ==========================
    def _find_downloaded_file(self):
        try:
            safe_title = safe_filename(self.item.title)
            pattern = os.path.join(self.item.output_path, f"{safe_title}*")
            files = glob.glob(pattern)
            if not files:
                return ""
            return max(files, key=os.path.getctime)
        except Exception as e:
            print("Erro ao localizar arquivo:", e)
            return ""