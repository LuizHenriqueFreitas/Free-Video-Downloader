import time
import pytest
from PySide6.QtCore import QObject, Signal, QThread

from services.download_service import DownloadService


# ==========================
# FAKE ITEM
# ==========================
class FakeItem:
    def __init__(self, id):
        self.id = str(id)
        self.title = f"Video {id}"
        self.status = "pending"


# ==========================
# FAKE WORKER
# ==========================
class FakeWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(object, str)
    cancelled = Signal(object)

    def __init__(self, item, delay=0.1):
        super().__init__()
        self.item = item
        self.delay = delay
        self._cancelled = False

    def run(self):
        # simula progresso
        for i in range(0, 101, 20):
            if self._cancelled:
                self.cancelled.emit(self.item)
                return

            time.sleep(self.delay)
            self.progress.emit(i)

        self.finished.emit(self.item)

    def cancel(self):
        self._cancelled = True

    def test_should_cancel_download(qtbot):
        service = TestableDownloadService()

        cancelled = []

        def on_cancel(item):
            cancelled.append(item.id)

        item = FakeItem(1)

        service.start_download(
            item,
            lambda x: None,
            lambda x: None,
            lambda x, m: None,
            on_cancel
        )

        # cancela rápido
        qtbot.wait(100)
        service.cancel_download(item.id)

        qtbot.waitUntil(lambda: len(cancelled) == 1, timeout=3000)

        assert cancelled[0] == "1"


# ==========================
# SERVICE CUSTOMIZADO
# ==========================
class TestableDownloadService(DownloadService):
    def _start_thread(self, item, on_progress, on_finished, on_error, on_cancel):
        thread = QThread()
        worker = FakeWorker(item)

        worker.moveToThread(thread)

        self.threads[item.id] = thread
        self.workers[item.id] = worker

        thread.started.connect(worker.run)

        worker.progress.connect(on_progress)
        worker.finished.connect(lambda: self._handle_finished(item, on_finished))
        worker.cancelled.connect(lambda: self._handle_cancel(item, on_cancel))

        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)

        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()


# ==========================
# TESTE PRINCIPAL
# ==========================
def test_download_flow_should_respect_queue_and_limit(qtbot):
    service = TestableDownloadService()

    results = []
    progress_calls = []

    def on_progress(value):
        progress_calls.append(value)

    def on_finished(item):
        results.append(item.id)

    def on_error(item, msg):
        pytest.fail("Não deveria dar erro")

    def on_cancel(item):
        pass

    # cria 5 downloads
    items = [FakeItem(i) for i in range(5)]

    for item in items:
        service.start_download(
            item,
            on_progress,
            on_finished,
            on_error,
            on_cancel
        )

    # espera terminar
    qtbot.waitUntil(lambda: len(results) == 5, timeout=5000)

    # ==========================
    # ASSERTS
    # ==========================
    assert len(results) == 5

    # ordem pode variar, mas todos devem completar
    assert set(results) == set(str(i) for i in range(5))

    # progresso foi chamado
    assert len(progress_calls) > 0

    # nunca ultrapassa limite de concorrência
    assert service.running <= service.max_downloads
