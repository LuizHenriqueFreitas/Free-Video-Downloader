# main.py

import sys

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from core import i18n
from core.utils import resource_path
from storage.settings_store import SettingsStore
from ui.main_window import MainWindow


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