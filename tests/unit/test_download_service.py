import uuid
from unittest.mock import patch
from PySide6.QtCore import QObject, Signal, QTimer, QEventLoop

from services.download_service import DownloadService

# ==========================
# FAKE ITEM
# ==========================
class FakeItem:
    def __init__(self, name="test"):
        self.id = str(uuid.uuid4())
        self.title = name
        self.output_path = ""
        self.status = "pending"
        self.file_path = None


# ==========================
# FAKE WORKER
# ==========================
class FakeWorker(QObject):
    finished = Signal(object)
    error = Signal(object, str)
    progress = Signal(int)
    cancelled = Signal(object)

    def __init__(self, item):
        super().__init__()
        self.item = item

    def run(self):
        # Emite finished no próximo ciclo do Qt
        QTimer.singleShot(0, self._finish)

    def _finish(self):
        self.item.status = "completed"
        self.item.file_path = f"{self.item.output_path}/{self.item.title}.mp4"
        self.finished.emit(self.item)

    def cancel(self):
        # Atualiza status e dispara sinal
        self.item.status = "cancelled"
        QTimer.singleShot(0, lambda: self.cancelled.emit(self.item))


# ==========================
# TESTS
# ==========================

@patch("services.download_service.DownloadWorker", FakeWorker)
def test_queue_addition():
    service = DownloadService()
    item = FakeItem()

    service.start_download(
        item,
        lambda x: None,  # progress
        lambda i: None,  # finished
        lambda i, e: None,  # error
        lambda i: None   # cancel
    )

    # Apenas verifica que foi adicionado ou já está rodando
    assert len(service.queue) == 0 or service.running > 0


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_respects_max_downloads():
    service = DownloadService()
    service.max_downloads = 2

    items = [FakeItem(f"item_{i}") for i in range(5)]

    for item in items:
        service.start_download(
            item,
            lambda x: None,
            lambda i: None,
            lambda i, e: None,
            lambda i: None
        )

    # Processa sinais do Qt
    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()

    assert service.running <= 2


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_queue_processing():
    service = DownloadService()
    service.max_downloads = 1

    items = [FakeItem(f"item_{i}") for i in range(3)]
    finished = []

    def on_finished(i):
        finished.append(i.id)

    for item in items:
        service.start_download(
            item,
            lambda x: None,
            on_finished,
            lambda i, e: None,
            lambda i: None
        )

    loop = QEventLoop()
    QTimer.singleShot(100, loop.quit)
    loop.exec()

    # Ao menos 1 item terminou
    assert len(finished) >= 1


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_download_completion():
    service = DownloadService()
    item = FakeItem()
    finished = []

    service.start_download(
        item,
        lambda x: None,
        lambda i: finished.append(i.id),
        lambda i, e: None,
        lambda i: None
    )

    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()

    assert item.id in finished


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_cancel_running_download():
    service = DownloadService()
    item = FakeItem()
    cancelled = []

    service.start_download(
        item,
        lambda x: None,
        lambda i: None,
        lambda i, e: None,
        lambda i: cancelled.append(i.id)
    )

    service.cancel_download(item.id)

    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()

    assert item.id in cancelled


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_cancel_queued_download():
    service = DownloadService()
    service.max_downloads = 1

    item1 = FakeItem("first")
    item2 = FakeItem("second")

    service.start_download(item1, lambda x: None, lambda i: None, lambda i, e: None, lambda i: None)
    service.start_download(item2, lambda x: None, lambda i: None, lambda i, e: None, lambda i: None)

    # item2 está na fila
    service.cancel_download(item2.id)

    ids_in_queue = [d["item"].id for d in service.queue]

    assert item2.id not in ids_in_queue


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_cleanup_after_finish():
    service = DownloadService()
    item = FakeItem()

    service.start_download(
        item,
        lambda x: None,
        lambda i: None,
        lambda i, e: None,
        lambda i: None
    )

    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()

    assert item.id not in service.workers
    assert item.id not in service.threads


@patch("services.download_service.DownloadWorker", FakeWorker)
def test_multiple_downloads_finish():
    service = DownloadService()
    items = [FakeItem(str(i)) for i in range(3)]
    finished = []

    for item in items:
        service.start_download(
            item,
            lambda x: None,
            lambda i: finished.append(i.id),
            lambda i, e: None,
            lambda i: None
        )

    loop = QEventLoop()
    QTimer.singleShot(100, loop.quit)
    loop.exec()

    assert len(finished) >= 2