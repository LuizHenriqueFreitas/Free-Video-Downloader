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

            command = self._build_command()
            success = self._run_process(command)

            if not success:
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
            "--no-part",              # Evita arquivos .part que atrapalham a verificação
            "--no-check-certificates",
        ]

        # Cookies
        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        # JS Runtime
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

        # MP4 - SEMPRE a MAIOR QUALIDADE disponível
        if self.item.format_type.upper() == "MP4":
            # Seleção de formato: prioriza vídeo mp4 + áudio m4a, fallback para qualquer combinação que funcione
            # Usa os clientes que dão acesso a streams DASH de alta resolução
            video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            
            command += [
                "--extractor-args", "youtube:player_client=web_safari,android_vr",
                "-f", video_format,
                "--merge-output-format", "mp4",
                "--postprocessor-args", "ffmpeg:-c:v copy -c:a aac",  # opcional, garante aac
                "--no-mtime",  # Não modifica timestamps, evita problemas
            ]
            return command

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

        last_percent = 0
        merge_started = False
        final_percent_emitted = False

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

            # Detecta início do merge
            if "Merging formats" in line:
                merge_started = True
                continue

            # Progresso do download
            if "[download]" in line and "%" in line:
                try:
                    percent_str = line.split("%")[0].split()[-1]
                    percent = float(percent_str)

                    # Se o merge já começou, ignora qualquer linha de progresso
                    if merge_started:
                        continue

                    # Emite apenas se for maior que o último e for < 100
                    # O 100% do stream não é emitido (será emitido no final)
                    if percent > last_percent and percent < 100:
                        last_percent = percent
                        self.progress.emit(int(percent))
                except:
                    pass

        self.process.wait()
        # Só emite 100% após o merge completo e uma única vez
        if not final_percent_emitted:
            self.progress.emit(100)
            final_percent_emitted = True

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