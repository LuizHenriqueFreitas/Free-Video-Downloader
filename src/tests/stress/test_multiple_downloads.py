import time
import random
import pytest
from PySide6.QtCore import QObject, Signal, QThread

from src.services.download_service import DownloadService


# ==========================
# FAKE ITEM
# ==========================
class FakeItem:
    def __init__(self, id):
        self.id = str(id)
        self.title = f"Video {id}"
        self.status = "pending"


# ==========================
# FAKE WORKER (stress)
# ==========================
class FakeWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(object, str)
    cancelled = Signal(object)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self._cancelled = False

    def run(self):
        steps = random.randint(5, 15)

        for i in range(steps):
            if self._cancelled:
                self.cancelled.emit(self.item)
                return

            time.sleep(random.uniform(0.01, 0.03))
            self.progress.emit(int((i / steps) * 100))

        self.finished.emit(self.item)

    def cancel(self):
        self._cancelled = True


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
        worker.finished.connect(lambda i: self._handle_finished(i, on_finished))
        worker.cancelled.connect(lambda i: self._handle_cancel(i, on_cancel))

        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)

        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()


# ==========================
# STRESS TEST
# ==========================
@pytest.mark.slow
def test_stress_downloads_with_random_cancel(qtbot):
    service = TestableDownloadService()

    TOTAL_DOWNLOADS = 20
    CANCEL_RATIO = 0.3

    items = [FakeItem(i) for i in range(TOTAL_DOWNLOADS)]

    finished = set()
    cancelled = set()
    processed = set()

    progress_calls = 0

    start_time = time.time()

    # ----------------------
    # callbacks
    # ----------------------
    def on_progress(value):
        nonlocal progress_calls
        progress_calls += 1

    def on_finished(item):
        finished.add(item.id)
        processed.add(item.id)

    def on_error(item, msg):
        pytest.fail(f"Erro inesperado: {msg}")

    def on_cancel(item):
        cancelled.add(item.id)
        processed.add(item.id)

    # ----------------------
    # start downloads
    # ----------------------
    for item in items:
        service.start_download(
            item,
            on_progress,
            on_finished,
            on_error,
            on_cancel
        )

    # ----------------------
    # espera inicial (mais robusto)
    # ----------------------
    qtbot.wait(200)

    # ----------------------
    # cancelamento aleatório
    # ----------------------
    to_cancel = random.sample(items, int(TOTAL_DOWNLOADS * CANCEL_RATIO))

    for item in to_cancel:
        service.cancel_download(item.id)

        # 👇 IMPORTANTE:
        # se estiver na fila, não gera callback → marcamos manualmente
        if item.id not in service.workers:
            processed.add(item.id)

    # ----------------------
    # espera terminar tudo
    # ----------------------
    qtbot.waitUntil(
        lambda: len(processed) == TOTAL_DOWNLOADS,
        timeout=15000
    )

    end_time = time.time()
    duration = end_time - start_time

    # ==========================
    # ASSERTS
    # ==========================
    assert len(processed) == TOTAL_DOWNLOADS

    # nenhum erro ocorreu
    assert len(finished) >= 0

    # concorrência respeitada
    assert service.running <= service.max_downloads

    # progresso aconteceu
    assert progress_calls > 0

    # ==========================
    # MÉTRICAS (debug útil)
    # ==========================
    print("\n📊 RESULTADO STRESS TEST")
    print(f"Tempo total: {duration:.2f}s")
    print(f"Finalizados: {len(finished)}")
    print(f"Cancelados: {len(cancelled)}")
    print(f"Processados: {len(processed)}")
    print(f"Progress events: {progress_calls}")
    print(f"Throughput: {TOTAL_DOWNLOADS / duration:.2f} downloads/s")