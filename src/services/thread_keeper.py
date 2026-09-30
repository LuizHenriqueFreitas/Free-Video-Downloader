# services/thread_keeper.py

""" Safe lifetime for QThread + worker pairs.

    A QThread (or its worker) created in Python is deleted as soon as the last
    Python reference is gone. If that happens while the thread is still
    running - even inside its own "finished" signal, which is emitted right
    before the thread really stops - Qt aborts the whole app
    ("QThread: Destroyed while thread is still running" is fatal on Qt 6).
    Mixing that with deleteLater() makes it a race that depends on the
    computer speed (it crashed the trimmer preview on some PCs).

    keep_thread() holds the thread and its objects until the thread has
    really stopped (wait()), and releases them on the main thread. Callers
    must NOT connect deleteLater() on them: Python deletes them afterwards.
"""

from PySide6.QtCore import QCoreApplication, QObject, Slot

# thread -> objects kept alive together with it (worker, ...)
_LIVE = {}
_reaper = None


# lives on the main thread, so "finished" arrives there (queued connection)
class _Reaper(QObject):
    @Slot()
    def reap(self):
        thread = self.sender()
        if thread is None:
            return
        # "finished" is emitted just before the thread stops: wait the real end
        thread.wait()
        _LIVE.pop(thread, None)


def keep_thread(thread, *objects):
    global _reaper
    if _reaper is None:
        _reaper = _Reaper()
        app = QCoreApplication.instance()
        if app is not None:
            _reaper.moveToThread(app.thread())
    _LIVE[thread] = objects
    thread.finished.connect(_reaper.reap)


# threads still kept (not finished yet) - used by tests
def live_threads():
    return list(_LIVE)
