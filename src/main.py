# main.py

import faulthandler
import os
import sys

""" Trimmer player (Qt Multimedia, FFmpeg backend): software decoding only.
    By default it tries GPU decoding first (DXVA2/D3D11VA) and, depending on the
    video driver, that initialisation crashes or freezes the whole app when
    the preview starts playing. The preview is a 240p file, the CPU decodes it
    easily. Set before Qt Multimedia loads; an existing value wins (debug).
    "none" isn't a device type, so the allowed list ends up empty.
"""
os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", "none")
os.environ.setdefault("QT_DISABLE_HW_TEXTURES_CONVERSION", "1")

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from core import i18n
from core.utils import resource_path, get_user_data_dir
from storage.settings_store import SettingsStore
from ui.main_window import MainWindow

# kept open while the app runs (faulthandler writes to it at a crash)
_crash_log = None


""" A native crash (Qt / driver) closes the packaged app without any message
    (there's no console). faulthandler writes the python stack of every
    thread to data/crash.log when that happens, so the failing step is known.
"""
def _enable_crash_log():
    global _crash_log
    try:
        path = os.path.join(get_user_data_dir(), "crash.log")
        # don't let it grow forever
        if os.path.exists(path) and os.path.getsize(path) > 1024 * 1024:
            os.remove(path)
        _crash_log = open(path, "a", encoding="utf-8")
        faulthandler.enable(file=_crash_log, all_threads=True)
    except Exception:
        pass


# output emojis and UTF-8 configuration
def _harden_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# own taskbar identity on Windows, so the taskbar shows the app icon
# (running by main.py it would group with python.exe)
def _set_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GetMediaFree.App")
    except Exception:
        pass


# Qt own texts (QMessageBox Ok/Cancel/Yes/No, QFileDialog) come in english;
# load the official Qt translation when the app isn't in english
def _install_qt_translator(app, language):
    if language == "en":
        return
    translator = QTranslator(app)
    # packaged app: PyInstaller ships them at _internal/PySide6/translations
    folders = (QLibraryInfo.path(QLibraryInfo.TranslationsPath), resource_path("PySide6/translations"))
    for folder in folders:
        if translator.load(f"qtbase_{language}", folder):
            app.installTranslator(translator)
            return


def main():
    _harden_stdio()
    _enable_crash_log()
    _set_windows_app_id()

    # before any window: every text is translated when the widget is built
    i18n.set_language(i18n.resolve_language(SettingsStore()))

    app = QApplication(sys.argv)
    _install_qt_translator(app, i18n.get_language())

    app.setStyle("Fusion")
    # window + taskbar icon (the .exe file icon is set by packaging/GetMediaFree.spec)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()