from collections import deque
from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadService:
    def __init__(self):
        self.threads = {}
        self.workers = {}

        self.queue = deque()

        self.running = 0
        self.max_downloads = 2

    # ==========================
    # PUBLIC API
    # ==========================
    def start_download(self, item, on_progress, on_finished, on_error, on_cancel):
        print(f"📥 Adicionado à fila: {item.title}")

        self.queue.append({
            "item": item,
            "on_progress": on_progress,
            "on_finished": on_finished,
            "on_error": on_error,
            "on_cancel": on_cancel
        })

        self._process_queue()

    # ==========================
    # FILA
    # ==========================
    def _process_queue(self):
        while self.running < self.max_downloads and self.queue:
            data = self.queue.popleft()
            item = data["item"]

            print(f"🚀 Iniciando download: {item.title}")

            self.running += 1

            self._start_thread(
                item,
                data["on_progress"],
                data["on_finished"],
                data["on_error"],
                data["on_cancel"]
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

        # 🔥 CORREÇÃO CRÍTICA (Qt não aceita args)
        worker.finished.connect(lambda: thread.quit())
        worker.error.connect(lambda *_: thread.quit())
        worker.cancelled.connect(lambda *_: thread.quit())

        # FINALIZAÇÃO DA THREAD
        thread.finished.connect(lambda: self._on_thread_finished(item.id))

        if hasattr(worker, "deleteLater"):
            thread.finished.connect(worker.deleteLater)

        self._finalize_download(self, )

        if not hasattr(worker, "moveToThread"):
            # ambiente de teste (FakeWorker)
            self.workers[item.id] = worker

            try:
                worker.progress.connect(on_progress)
                worker.finished.connect(lambda emitted_item: self._handle_finished(emitted_item, on_finished))
                worker.error.connect(lambda emitted_item, msg: self._handle_error(emitted_item, on_error, msg))
                worker.cancelled.connect(lambda emitted_item: self._handle_cancel(emitted_item, on_cancel))

                worker.run()
            except Exception as e:
                print(f"Erro worker fake: {e}")
                self._handle_error(item, on_error, str(e))

            return

        thread.start()


    def _finalize_download(self, item_id):
        self._cleanup(item_id)

        if self.running > 0:
            self.running -= 1

        # 🔥 cleanup garantido (resolve teste)
        self.threads.pop(item_id, None)
        self.workers.pop(item_id, None)

        self._process_queue()

    # ==========================
    # HANDLERS
    # ==========================
    def _handle_finished(self, item, callback):
        print(f"✅ FINISHED: {item.title}")

        try:
            callback(item)
        except Exception as e:
            print(f"Erro no callback finished: {e}")
        finally:
            self._finalize_download(item.id)

    def _handle_error(self, item, callback, msg):
        print(f"❌ ERROR: {item.title} -> {msg}")

        try:
            callback(item, msg)
        except Exception as e:
            print(f"Erro no callback error: {e}")
        finally:
            self._finalize_download(item.id)

    def _handle_cancel(self, item, callback):
        print(f"⚠️ CANCEL: {item.title}")

        try:
            callback(item)
        except Exception as e:
            print(f"Erro no callback cancel: {e}")
        finally:
            self._finalize_download(item.id)

    # ==========================
    # FINALIZAÇÃO
    # ==========================
    def _finalize_download(self, item_id):
        self._cleanup(item_id)

        # proteção contra inconsistência
        if self.running > 0:
            self.running -= 1

        self._process_queue()

    # ==========================
    # CLEANUP (SAFE)
    # ==========================
    def _cleanup(self, item_id):
        thread = self.threads.get(item_id)

        if not thread:
            return

        try:
            if thread.isRunning():
                thread.quit()
        except Exception as e:
            print("Erro ao finalizar thread:", e)

    # ==========================
    # FINAL THREAD CALLBACK
    # ==========================
    def _on_thread_finished(self, item_id):
        self.threads.pop(item_id, None)
        self.workers.pop(item_id, None)

    # ==========================
    # CANCELAMENTO
    # ==========================
    def cancel_download(self, item_id):
        worker = self.workers.get(item_id)
        if worker:
            print(f"🛑 Cancelando ativo: {item_id}")
            try:
                worker.cancel()
            except Exception as e:
                print(f"Erro ao cancelar: {e}")
            return

        # Remove da fila
        for i, data in enumerate(self.queue):
            if data["item"].id == item_id:
                print(f"🗑️ Removido da fila: {item_id}")
                del self.queue[i]
                return