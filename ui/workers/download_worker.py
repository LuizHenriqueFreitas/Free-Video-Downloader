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
    cookies_exists,
    is_youtube,
    safe_filename,
)


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
            self.item.status = "downloading"
            # sinaliza que SAIU da fila e realmente começou (card vira "Baixando")
            self.progress.emit(0)

            # Limpa arquivos residuais do yt-dlp
            safe_title = safe_filename(self.item.title)
            base = os.path.join(self.item.output_path, safe_title)
            patterns = [f"{base}*.part", f"{base}*.ytdl", f"{base}*.temp", f"{base}*.frag*"]
            for pattern in patterns:
                for f in glob.glob(pattern):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

            # Construir comando e executar
            command = self._build_command()
            success = self._run_process(command)

            if not success:
                if self.item.status == "cancelled":
                    return
                raise Exception("Falha no download (yt-dlp retornou erro)")

            final_path = self._find_downloaded_file()
            if not final_path or not os.path.exists(final_path):
                raise Exception("Arquivo final não encontrado")

            self.item.file_path = final_path
            self.item.status = "completed"
            self.finished.emit(self.item)

        except Exception as e:
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
            "--newline",   # progresso em linhas separadas (parsing confiável)
        ]

        if cookies_exists():
            command += ["--cookies", get_cookies_path()]

        node_path = get_node_path()
        if node_path and os.path.exists(node_path):
            command += ["--js-runtime", f"node:{node_path}"]
        else:
            command += ["--js-runtime", "node"]

        # Sobrescrever arquivo existente (decidido na UI)
        if getattr(self.item, "overwrite", False):
            command += ["--force-overwrites"]

        # Corte de trecho (apenas parte do vídeo)
        section_args = self._build_section_args()

        # MP3
        if self.item.format_type.upper() == "MP3":
            command += [
                "-f", "bestaudio",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "192K",
            ]
            command += section_args
            return command

        # MP4
        if self.item.format_type.upper() == "MP4":
            # Valida o quality_id: se for algo como "1080p" (texto), não funciona.
            # Nesse caso, usa fallback.
            if self.item.quality_id and "+" in self.item.quality_id:
                video_format = self.item.quality_id
            else:
                video_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

            # extractor-args específicos do YouTube só quando a URL é do YouTube
            if is_youtube(self.item.url):
                command += ["--extractor-args", "youtube:player_client=web_safari,android_vr"]

            command += [
                "-f", video_format,
                "--merge-output-format", "mp4",
                "--no-mtime",
                "--no-continue",
            ]

            if section_args:
                # ao cortar, deixamos o yt-dlp/ffmpeg reencodar nos limites
                # (force-keyframes-at-cuts) para um corte preciso.
                command += section_args
            else:
                # sem corte: cópia direta de stream (rápido)
                command += ["--postprocessor-args", "ffmpeg:-c:v copy -c:a aac"]

            return command

        return command

    # ==========================
    # SECTION (CORTE DE TRECHO)
    # ==========================
    def _build_section_args(self):
        start = getattr(self.item, "clip_start", None)
        end = getattr(self.item, "clip_end", None)

        if start is None and end is None:
            return []

        start_s = max(0.0, float(start)) if start is not None else 0.0
        end_str = f"{float(end):.3f}" if end is not None else "inf"

        section = f"*{start_s:.3f}-{end_str}"
        return [
            "--download-sections", section,
            "--force-keyframes-at-cuts",
            # Força decodificação por SOFTWARE no ffmpeg. Sem isso, o ffmpeg tenta
            # aceleração por hardware (dxva2) na decodificação do h264 e, em
            # algumas GPUs/drivers, falha com "Could not create the surfaces" e
            # o corte trava indefinidamente.
            "--downloader-args", "ffmpeg_i:-hwaccel none",
        ]

    # ==========================
    # PROCESS
    # ==========================
    def _run_process(self, command):
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
            creationflags=creationflags,
        )

        last_emitted = -1
        merge_started = False

        # Lê o stdout linha a linha (sem print por linha — custo desnecessário).
        for line in self.process.stdout:
            if self._is_cancelled:
                break
            if not line:
                continue
            line = line.strip()

            if "Merging formats" in line:
                merge_started = True
                continue

            if "[download]" in line and "%" in line:
                try:
                    percent = float(line.split("%")[0].split()[-1])
                    if merge_started:
                        continue
                    # Progresso MONOTÔNICO, travado em 99 até o fim. Em vídeos com
                    # vídeo+áudio separados, o 2º stream recomeça em 0% — como só
                    # emitimos valores maiores, a barra fica parada em 99 durante o
                    # 2º stream e a junção (merge), dando bom feedback, e só vai a
                    # 100 quando tudo termina.
                    p = min(99, int(percent))
                    if p > last_emitted:
                        last_emitted = p
                        self.progress.emit(p)
                except Exception:
                    pass

        # Cancelado: mata a árvore de processos e encerra rápido
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
        self.progress.emit(100)   # 100% uma única vez no fim
        return self.process.returncode == 0

    # ==========================
    # CANCEL
    # ==========================
    def cancel(self):
        self._is_cancelled = True
        # mata yt-dlp E seus filhos (ffmpeg), liberando o pipe imediatamente
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