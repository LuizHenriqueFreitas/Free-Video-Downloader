import pytest
from unittest.mock import patch
import io

from src.ui.workers.download_worker import DownloadWorker, safe_filename


# ==========================
# MOCK ITEM
# ==========================

class FakeItem:
    def __init__(self):
        self.id = "123"
        self.title = "video:test*illegal?"
        self.url = "http://youtube.com/test"
        self.output_path = "downloads"
        self.format_type = "MP4"
        self.quality = "1080p"
        self.quality_id = None
        self.status = "pending"
        self.file_path = None

class FakeProcess:
    def __init__(self, lines, returncode=0):
        self.lines = lines
        self.returncode = returncode
        self.stdout = self
        self.killed = False
        self._iter = iter(lines)

    def __iter__(self):
        return self._iter

    def __next__(self):
        return next(self._iter)

    def wait(self):
        return self.returncode

    def kill(self):
        self.killed = True


# ==========================
# TEST: safe_filename
# ==========================

def test_safe_filename_remove_caracteres_invalidos():
    name = 'video:*?"<>|test'
    result = safe_filename(name)

    assert ":" not in result
    assert "*" not in result
    assert "?" not in result


# ==========================
# TEST: build command MP4
# ==========================

@patch("ui.workers.download_worker.get_node_path", return_value="node.exe")
@patch("ui.workers.download_worker.get_ytdlp_path", return_value="yt-dlp.exe")
@patch("ui.workers.download_worker.get_ffmpeg_path", return_value="ffmpeg/")
@patch("ui.workers.download_worker.cookies_exists", return_value=False)
def test_build_command_mp4(_, __, ___, ____):
    item = FakeItem()
    worker = DownloadWorker(item)

    cmd = worker._build_command()

    format_index = cmd.index("-f") + 1
    format_arg = cmd[format_index]

    assert "yt-dlp.exe" in cmd
    assert "--merge-output-format" in cmd
    assert "mp4" in cmd



# ==========================
# TEST: build command MP3
# ==========================

@patch("ui.workers.download_worker.get_node_path", return_value="node.exe")
@patch("ui.workers.download_worker.get_ytdlp_path", return_value="yt-dlp.exe")
@patch("ui.workers.download_worker.get_ffmpeg_path", return_value="ffmpeg/")
def test_build_command_mp3(_, __, ___):
    item = FakeItem()
    item.format_type = "MP3"

    worker = DownloadWorker(item)
    cmd = worker._build_command()

    assert "-x" in cmd
    assert "--audio-format" in cmd
    assert "mp3" in cmd


# ==========================
# MOCK PROCESS
# ==========================

class FakeProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = io.StringIO("\n".join(lines))
        self.returncode = returncode
        self.killed = False

    def wait(self):
        return self.returncode

    def kill(self):
        self.killed = True


# ==========================
# TEST: progresso do download com merge (feedback correto)
# ==========================

@patch("ui.workers.download_worker.subprocess.Popen")
def test_run_process_progresso_com_merge(mock_popen):
    """
    Verifica que o progresso é emitido corretamente:
    - Emite valores de 0 a 99 durante o download.
    - Ignora o 100% da linha de download (stream completo).
    - Emite 100% apenas uma vez após o merge.
    """
    lines = [
        "[download]   10.0%",
        "[download]   50.0%",
        "[download]   99.0%",
        "[download]  100.0%",      # stream de vídeo completo – deve ser ignorado
        "[Merger] Merging formats into file.mp4",
    ]
    mock_popen.return_value = FakeProcess(lines, returncode=0)
    worker = DownloadWorker(FakeItem())
    progresses = []
    worker.progress.connect(progresses.append)

    result = worker._run_process(["cmd"])

    assert result is True
    expected = [10, 50, 99, 100]
    assert progresses == expected, f"Progressos emitidos: {progresses}, esperado: {expected}"

# ==========================
# TEST: cancelamento
# ==========================

@patch("ui.workers.download_worker.subprocess.Popen")
def test_cancel_durante_execucao(mock_popen):
    lines = [
        "[download]   10.0%",
        "[download]   20.0%",
    ]

    mock_popen.return_value = FakeProcess(lines)

    item = FakeItem()
    worker = DownloadWorker(item)

    cancelled_called = []
    worker.cancelled.connect(lambda i: cancelled_called.append(True))

    worker.cancel()  # cancela antes

    result = worker._run_process(["cmd"])

    assert result is False
    assert item.status == "cancelled"
    assert cancelled_called


# ==========================
# TEST: erro no processo
# ==========================

@patch("ui.workers.download_worker.subprocess.Popen")
def test_run_process_erro(mock_popen):
    mock_popen.return_value = FakeProcess([], returncode=1)

    item = FakeItem()
    worker = DownloadWorker(item)

    result = worker._run_process(["cmd"])

    assert result is False


# ==========================
# TEST: find downloaded file
# ==========================

@patch("ui.workers.download_worker.glob.glob")
@patch("ui.workers.download_worker.os.path.getctime")
def test_find_downloaded_file(mock_ctime, mock_glob):
    mock_glob.return_value = ["file1.mp4", "file2.mp4"]
    mock_ctime.side_effect = [1, 2]

    item = FakeItem()
    worker = DownloadWorker(item)

    result = worker._find_downloaded_file()

    assert result == "file2.mp4"


# ==========================
# TEST: fluxo completo de sucesso (run completo)
# ==========================

@patch.object(DownloadWorker, "_run_process", return_value=True)
@patch.object(DownloadWorker, "_find_downloaded_file", return_value="video.mp4")
@patch("ui.workers.download_worker.os.path.exists", return_value=True)   # ← NOVO
def test_fluxo_completo_sucesso(mock_exists, mock_find_file, mock_run_process):
    """Verifica que o worker completa o download com sucesso e atualiza o item."""
    item = FakeItem()
    worker = DownloadWorker(item)

    finished_called = []
    worker.finished.connect(lambda i: finished_called.append(i))

    worker.run()

    assert item.status == "completed"
    assert item.file_path == "video.mp4"
    assert finished_called == [item]
    mock_run_process.assert_called_once()
    mock_find_file.assert_called_once()
    mock_exists.assert_called_with("video.mp4")  

# ==========================
# TEST: fluxo completo ERROR
# ==========================

@patch.object(DownloadWorker, "_run_process", return_value=False)
def test_run_completo_erro(_):
    item = FakeItem()
    worker = DownloadWorker(item)

    error_called = []
    worker.error.connect(lambda i, msg: error_called.append(msg))

    worker.run()

    assert item.status == "error"
    assert error_called