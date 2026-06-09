#main.py

import sys

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def _harden_stdio():
    """
    Evita que prints de debug com emojis (📥, 🚀, ✅...) derrubem a aplicação
    em consoles Windows com code page cp1252. Reconfigura stdout/stderr para
    UTF-8 com 'replace' quando possível; em modo janela (sem console) os
    streams podem ser None e simplesmente ignoramos.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _harden_stdio()

    app = QApplication(sys.argv)

    # estilo opcional (dark básico)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()