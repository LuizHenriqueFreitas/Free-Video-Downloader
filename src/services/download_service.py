# services/download_service.py

from collections import deque
from threading import RLock
from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadService:
    """
    It manages a single download queue with a limit on simultaneous
    executions (max. 3); remaining tasks wait in the queue.

    Completion handlers are connected as functions (direct connection)
    running within the worker thread itself—allowing the thread to
    terminate cleanly. UI safety is ensured by the consumer
    (MainWindow), whose callbacks merely emit marshaled signals to the
    main thread.

    Since `start_download` (main thread) and the completion handlers
    (worker thread) modify `queue` and `running`, all state mutations
    are protected by an RLock—preventing race conditions that previously
    left items stuck in the queue.

    The API (start_download / queue / running / max_downloads / workers /
    threads / cancel_download) is kept stable for testing purposes.
    """

    def __init__(self):
        self.threads = {}
        self.workers = {}

        self.queue = deque()

        self.running = 0
        self.max_downloads = 3

        self._lock = RLock()

    # ==========================
    # PUBLIC API
    # ==========================
    def start_download(self, item, on_progress, on_finished, on_error, on_cancel):
        with self._lock:
            self.queue.append({
                "item": item,
                "on_progress": on_progress,
                "on_finished": on_finished,
                "on_error": on_error,
                "on_cancel": on_cancel,
            })
            self._process_queue()

    # ==========================
    # QUEUE
    # ==========================
    def _process_queue(self):
        with self._lock:
            while self.running < self.max_downloads and self.queue:
                data = self.queue.popleft()
                item = data["item"]

                self.running += 1
                self._start_thread(
                    item,
                    data["on_progress"],
                    data["on_finished"],
                    data["on_error"],
                    data["on_cancel"],
                )

    # ==========================
    # THREAD START
    # ==========================
    def _start_thread(self, item, on_progress, on_finished, on_error, on_cancel):
        thread = QThread()
        worker = DownloadWorker(item)

        worker.moveToThread(thread)

        self.threads[item.id] = thread
        self.workers[item.id] = worker

        # START
        thread.started.connect(worker.run)

        # SIGNALS
        worker.progress.connect(on_progress)

        worker.finished.connect(
            lambda emitted_item: self._handle_finished(emitted_item, on_finished)
        )
        worker.error.connect(
            lambda emitted_item, msg: self._handle_error(emitted_item, on_error, msg)
        )
        worker.cancelled.connect(
            lambda emitted_item: self._handle_cancel(emitted_item, on_cancel)
        )

        # Terminate the thread when the worker finishes (Qt does not accept arguments here)
        worker.finished.connect(lambda *_: thread.quit())
        worker.error.connect(lambda *_: thread.quit())
        worker.cancelled.connect(lambda *_: thread.quit())

        # Final cleanup of references when the thread actually terminates.
        thread.finished.connect(lambda: self._on_thread_finished(item.id))
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()

    # ==========================
    # HANDLERS
    # ==========================
    def _handle_finished(self, item, callback):
        try:
            callback(item)
        except Exception as e:
            print(f"Erro no callback finished: {e}")
        finally:
            self._finalize_download(item.id)

    def _handle_error(self, item, callback, msg):
        try:
            callback(item, msg)
        except Exception as e:
            print(f"Erro no callback error: {e}")
        finally:
            self._finalize_download(item.id)

    def _handle_cancel(self, item, callback):
        try:
            callback(item)
        except Exception as e:
            print(f"Erro no callback cancel: {e}")
        finally:
            self._finalize_download(item.id)

    # ==========================
    # FINALIZATION
    # ==========================
    def _finalize_download(self, item_id):
        # frees up the slot and processes the next one in the queue
        with self._lock:
            if self.running > 0:
                self.running -= 1
            self._process_queue()

    def _on_thread_finished(self, item_id):
        # Remove references only after the thread has actually finished.
        with self._lock:
            self.threads.pop(item_id, None)
            self.workers.pop(item_id, None)

    # ==========================
    # APP SHUTDOWN
    # ==========================
    def shutdown(self, timeout_ms=4000):
        """
        Cancels everything and waits for the threads to finish, so the app closes without the
        'QThread: Destroyed while thread is still running' warning..
        """
        with self._lock:
            self.queue.clear()
            active_ids = list(self.workers.keys())
            threads = list(self.threads.values())

        for item_id in active_ids:
            try:
                self.cancel_download(item_id)   # kill yt-dlp+ffmpeg (taskkill)
            except Exception:
                pass

        for thread in threads:
            try:
                thread.quit()
                thread.wait(timeout_ms)
            except Exception:
                pass

    # ==========================
    # CANCELING
    # ==========================
    def cancel_download(self, item_id):
        # 1) Active download: acquires the worker under a lock but calls cancel().
        #    OUTSIDE the lock (taskkill might block briefly).
        with self._lock:
            worker = self.workers.get(item_id)

        if worker:
            try:
                worker.cancel()
            except Exception as e:
                print(f"Erro ao cancelar: {e}")
            return

        # 2) Still in the queue: removes it and notifies the UI (did not occupy a slot)
        cancelled_item = None
        on_cancel = None
        with self._lock:
            for i, data in enumerate(self.queue):
                if data["item"].id == item_id:
                    del self.queue[i]
                    cancelled_item = data["item"]
                    cancelled_item.status = "cancelled"
                    on_cancel = data["on_cancel"]
                    break

        if cancelled_item is not None and on_cancel is not None:
            try:
                on_cancel(cancelled_item)
            except Exception as e:
                print(f"Erro no callback cancel (fila): {e}")
