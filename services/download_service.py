# services/download_service.py

from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadService:
    def __init__(self):
        self.active_downloads = {}

    def start_download(self, item, on_progress, on_finished, on_error, on_cancel):
        thread = QThread()
        worker = DownloadWorker(item)

        worker.moveToThread(thread)

        self.active_downloads[item.id] = {
            "thread": thread,
            "worker": worker
        }

        # START
        thread.started.connect(worker.run)

        # SIGNALS
        worker.progress.connect(on_progress)

        worker.finished.connect(lambda i: self._finish(item.id, on_finished, i))
        worker.error.connect(lambda i, msg: self._error(item.id, on_error, i, msg))
        worker.cancelled.connect(lambda i: self._cancel(item.id, on_cancel, i))

        # THREAD CONTROL (CRÍTICO)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.cancelled.connect(thread.quit)

        thread.start()

    # ==========================
    # HANDLERS
    # ==========================

    def _finish(self, item_id, callback, item):
        print("✅ FINISHED")
        try:
            callback(item)
        finally:
            self._cleanup_safe(item_id)

    def _error(self, item_id, callback, item, msg):
        print("❌ ERROR:", msg)
        try:
            callback(item, msg)
        finally:
            self._cleanup_safe(item_id)

    def _cancel(self, item_id, callback, item):
        print("⚠️ CANCEL")
        try:
            callback(item)
        finally:
            self._cleanup_safe(item_id)

    # ==========================
    # CLEANUP SEGURO
    # ==========================
    def _cleanup_safe(self, item_id):
        if item_id not in self.active_downloads:
            return

        data = self.active_downloads[item_id]
        thread = data["thread"]
        worker = data["worker"]

        try:
            if thread.isRunning():
                thread.quit()

            worker.deleteLater()
            thread.deleteLater()

        except Exception as e:
            print("Erro cleanup:", e)

        del self.active_downloads[item_id]

    # ==========================
    # CANCEL
    # ==========================
    def cancel_download(self, item_id):
        if item_id in self.active_downloads:
            self.active_downloads[item_id]["worker"].cancel()