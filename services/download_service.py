from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadService:
    def __init__(self):
        self.active_downloads = {}

    def start_download(self, item, on_progress, on_finished, on_error, on_cancel):
        thread = QThread()
        worker = DownloadWorker(item)

        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.cancelled.connect(on_cancel)

        # cleanup correto
        worker.finished.connect(thread.quit)
        worker.error.connect(lambda *_: thread.quit())
        worker.cancelled.connect(lambda *_: thread.quit())

        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)

        self.active_downloads[item.id] = (thread, worker)

        thread.start()

    def cancel_download(self, item_id):
        if item_id in self.active_downloads:
            _, worker = self.active_downloads[item_id]
            worker.cancel()

    def cleanup(self, item_id):
        if item_id in self.active_downloads:
            del self.active_downloads[item_id]