# tests/unit/test_thread_keeper.py

""" Tests for services/thread_keeper.py with real QThreads.

    Before it, threads were released inside their own "finished" signal and
    also by deleteLater(): Qt aborted the app ("QThread: Destroyed while thread
    is still running") right after the trimmer preview download, on some PCs.
"""

import time

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal

from services.thread_keeper import keep_thread, live_threads


class _Worker(QObject):
    finished = Signal()

    def run(self):
        time.sleep(0.001)
        self.finished.emit()


def _start(n):
    for _ in range(n):
        thread = QThread()
        worker = _Worker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        keep_thread(thread, worker)
        thread.start()
        # caller drops its references at once (like a closed dialog)
        del thread, worker


def _wait_released(timeout=10):
    deadline = time.monotonic() + timeout
    while live_threads() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.005)


class TestKeepThread:

    def test_kept_until_finished_then_released(self):
        _start(1)
        assert len(live_threads()) == 1
        _wait_released()
        assert live_threads() == []

    def test_many_threads_without_references(self):
        # the old pattern aborted the process in this scenario
        _start(100)
        _wait_released()
        assert live_threads() == []

    def test_released_thread_really_stopped(self):
        # own references just to inspect them after thread_keeper releases
        threads = []
        for _ in range(5):
            thread = QThread()
            worker = _Worker()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            keep_thread(thread, worker)
            threads.append(thread)
            thread.start()
        _wait_released()
        assert live_threads() == []
        assert all(t.isFinished() for t in threads)
