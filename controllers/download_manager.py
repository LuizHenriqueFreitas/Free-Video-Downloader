#controller/download_manager
from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadManager:
    def __init__(self):
        self.active_downloads = []

    def start_download(self, item, on_progress, on_finished, on_error):
        thread = QThread()
        worker = DownloadWorker(
            url=item.url,
            format_type=item.format_type,
            quality=item.quality,
            output_path=item.output_path,
            filename=item.title,
        )

        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(on_progress)
        worker.finished.connect(lambda: on_finished(item))
        worker.error.connect(lambda msg: on_error(item, msg))

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self.active_downloads.append((thread, worker))

        thread.start()