from collections import deque
from threading import RLock
from PySide6.QtCore import QThread
from ui.workers.download_worker import DownloadWorker


class DownloadService:
    """
    Gerencia uma fila única de downloads com um limite de execuções
    simultâneas (máx. 3). Os demais ficam aguardando na fila.

    Os handlers de término são conectados como funções (conexão direta),
    executando na própria thread do worker — assim a thread encerra a si
    mesma de forma limpa. A segurança da UI é garantida pelo consumidor
    (MainWindow), cujos callbacks apenas emitem sinais marshalados para a
    thread principal.

    Como `start_download` (thread principal) e os handlers de término
    (thread do worker) mexem em `queue`/`running`, todas as mutações desse
    estado são protegidas por um RLock — evita corridas que deixavam itens
    presos na fila.

    A API (start_download / queue / running / max_downloads / workers /
    threads / cancel_download) é mantida estável para os testes.
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
    # FILA
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

        # Encerrar a thread quando o worker terminar (Qt não aceita args aqui)
        worker.finished.connect(lambda *_: thread.quit())
        worker.error.connect(lambda *_: thread.quit())
        worker.cancelled.connect(lambda *_: thread.quit())

        # Limpeza final das referências quando a thread realmente terminar
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
    # FINALIZAÇÃO
    # ==========================
    def _finalize_download(self, item_id):
        # libera o slot e processa o próximo da fila
        with self._lock:
            if self.running > 0:
                self.running -= 1
            self._process_queue()

    def _on_thread_finished(self, item_id):
        # remove referências só depois que a thread terminou de fato
        with self._lock:
            self.threads.pop(item_id, None)
            self.workers.pop(item_id, None)

    # ==========================
    # ENCERRAMENTO (fechar o app)
    # ==========================
    def shutdown(self, timeout_ms=4000):
        """
        Cancela tudo e aguarda as threads terminarem, para o app fechar sem o
        aviso 'QThread: Destroyed while thread is still running'.
        """
        with self._lock:
            self.queue.clear()
            active_ids = list(self.workers.keys())
            threads = list(self.threads.values())

        for item_id in active_ids:
            try:
                self.cancel_download(item_id)   # mata yt-dlp+ffmpeg (taskkill)
            except Exception:
                pass

        for thread in threads:
            try:
                thread.quit()
                thread.wait(timeout_ms)
            except Exception:
                pass

    # ==========================
    # CANCELAMENTO
    # ==========================
    def cancel_download(self, item_id):
        # 1) Download ativo: pega o worker sob lock, mas chama cancel()
        #    FORA do lock (taskkill pode bloquear por instantes).
        with self._lock:
            worker = self.workers.get(item_id)

        if worker:
            try:
                worker.cancel()
            except Exception as e:
                print(f"Erro ao cancelar: {e}")
            return

        # 2) Ainda na fila: remove e avisa a UI (não ocupava slot)
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
