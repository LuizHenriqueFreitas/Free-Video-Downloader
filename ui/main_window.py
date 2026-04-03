# ui/main_window.py

import os
import shutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QMessageBox, QFileDialog, QLabel, 
)
from PySide6.QtCore import Qt, QMetaObject, QObject, QThread, Signal, Q_ARG, Slot

from controllers.download_controller import DownloadController
from services.download_service import DownloadService
from services.updater import check_and_update, get_installed_version

from ui.components.download_card import DownloadCard
from ui.download_dialog import DownloadDialog

from core.utils import get_cookies_path, cookies_exists


# ==========================
# DOWNLOAD WORKER THREAD
# ==========================
class DownloadWorker(QObject):
    finished = Signal(object)
    progress = Signal(float)
    error = Signal(object, str)
    cancelled = Signal(object)

    def __init__(self, item, download_service):
        super().__init__()
        self.item = item
        self.download_service = download_service

    def run(self):
        try:
            self.download_service.start_download(
                self.item,
                on_progress=lambda v: self.progress.emit(v),
                on_finished=lambda i: self.finished.emit(i),
                on_error=lambda i, m: self.error.emit(i, m),
                on_cancel=lambda i: self.cancelled.emit(i)
            )
        except Exception as e:
            self.error.emit(self.item, str(e))


# ==========================
# MAIN WINDOW
# ==========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Video Downloader")
        self.setMinimumSize(900, 600)

        self.controller = DownloadController()
        self.download_service = DownloadService()

        self.cards = {}

        self._setup_ui()
        self._load_history()
        self._load_version()
        self._update_cookie_ui()

    # -------------------------
    # UI
    # -------------------------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        central.setLayout(layout)

        # TOP BAR
        top_bar = QHBoxLayout()

        self.new_button = QPushButton("+ Colar link")
        self.new_button.clicked.connect(self._open_download_dialog)

        self.update_button = QPushButton("Atualizar yt-dlp")
        self.update_button.clicked.connect(self._update_ytdlp)

        self.import_cookies_btn = QPushButton("Importar cookies")
        self.import_cookies_btn.clicked.connect(self._import_cookies)

        self.remove_cookies_btn = QPushButton("Remover cookies")
        self.remove_cookies_btn.clicked.connect(self._remove_cookies)

        self.cookies_status_label = QLabel("Cookies: ...")

        self.version_label = QPushButton("yt-dlp: ...")
        self.version_label.setEnabled(False)

        top_bar.addWidget(self.new_button)
        top_bar.addWidget(self.update_button)
        top_bar.addWidget(self.import_cookies_btn)
        top_bar.addWidget(self.remove_cookies_btn)
        top_bar.addWidget(self.cookies_status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.version_label)

        layout.addLayout(top_bar)

        # SCROLL AREA PARA CARDS
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    # -------------------------
    # VERSION & UPDATE
    # -------------------------
    def _load_version(self):
        version = get_installed_version()
        self.version_label.setText(f"yt-dlp: {version}")

    def _update_ytdlp(self):
        success, msg = check_and_update()
        self._safe_message("Atualização", msg)
        self._load_version()

    # -------------------------
    # HISTORY
    # -------------------------
    def _load_history(self):
        items = self.controller.get_history()
        for item in items:
            self._add_card(item, start_download=False)

    # -------------------------
    # COOKIES
    # -------------------------
    def _update_cookie_ui(self):
        if cookies_exists():
            self.cookies_status_label.setText("Cookies: OK")
            self.cookies_status_label.setStyleSheet("color: #4CAF50;")
            self.remove_cookies_btn.setEnabled(True)
        else:
            self.cookies_status_label.setText("Cookies: NÃO CONFIGURADO")
            self.cookies_status_label.setStyleSheet("color: #F44336;")
            self.remove_cookies_btn.setEnabled(False)

    def _import_cookies(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar cookies.txt",
            "",
            "Text Files (*.txt)"
        )

        if not file:
            return

        try:
            os.makedirs("data", exist_ok=True)
            shutil.copy(file, get_cookies_path())
            self._safe_message("Sucesso", "Cookies importados com sucesso!")
            self._update_cookie_ui()
        except Exception as e:
            self._safe_error("Erro", str(e))

    def _remove_cookies(self):
        try:
            path = get_cookies_path()
            if os.path.exists(path):
                os.remove(path)
                self._safe_message("Removido", "Cookies removidos.")
            else:
                self._safe_message("Info", "Nenhum cookie encontrado.")
            self._update_cookie_ui()
        except Exception as e:
            self._safe_error("Erro", str(e))

    # -------------------------
    # CARDS
    # -------------------------
    def _add_card(self, item, start_download=True):
        card = DownloadCard(item)
        self.cards[item.id] = card
        self.container_layout.insertWidget(0, card)

        if start_download:
            self._start_download(item, card)

    # -------------------------
    # DOWNLOAD DIALOG
    # -------------------------
    def _open_download_dialog(self):
        if not cookies_exists():
            self._safe_error(
                "Cookies necessários",
                "Você precisa importar o arquivo cookies.txt antes de baixar vídeos."
            )
            return

        dialog = DownloadDialog(self)
        if dialog.exec():
            item = dialog.get_result()
            if item:
                self.controller.add_item(item)
                self._add_card(item, start_download=True)

    # -------------------------
    # START DOWNLOAD (THREAD SAFE)
    # -------------------------
    def _start_download(self, item, card):
        card.update_status("downloading")

        # criar worker + thread
        worker = DownloadWorker(item, self.download_service)
        thread = QThread()
        worker.moveToThread(thread)

        # conectar sinais
        worker.progress.connect(lambda v: card.update_progress(v))
        worker.finished.connect(self._on_download_finished)
        worker.error.connect(self._on_download_error)
        worker.cancelled.connect(self._on_download_cancelled)

        # iniciar thread
        thread.started.connect(worker.run)
        thread.start()

        # salvar referência pra evitar garbage collector
        item._thread = thread
        item._worker = worker

        # cancelamento
        card.on_cancel = lambda: self.download_service.cancel_download(item.id)

    # -------------------------
    # CALLBACKS
    # -------------------------
    def _on_download_finished(self, item):
        card = self.cards.get(item.id)
        if card:
            card.update_status("completed")
        self.controller.update_item(item)

    def _on_download_error(self, item, msg):
        card = self.cards.get(item.id)
        if card:
            card.update_status("error")
        self.controller.update_item(item)
        self._safe_error("Erro", msg)

    def _on_download_cancelled(self, item):
        card = self.cards.get(item.id)
        if card:
            card.update_status("cancelled")
        self.controller.update_item(item)

    # -------------------------
    # SAFE UI
    # -------------------------
    def _safe_ui(self, func, *args):
        QMetaObject.invokeMethod(
            self,
            lambda: func(*args),
            Qt.QueuedConnection
        )

    def _safe_message(self, title, msg):
        if QThread.currentThread() == self.thread():
            QMessageBox.information(self, title, msg)
        else:
            QMetaObject.invokeMethod(self, "_show_message_box",
                                    Qt.QueuedConnection,
                                    Q_ARG(str, title),
                                    Q_ARG(str, msg),
                                    Q_ARG(int, QMessageBox.Information))

    def _safe_error(self, title, msg):
        if QThread.currentThread() == self.thread():
            QMessageBox.critical(self, title, msg)
        else:
            QMetaObject.invokeMethod(self, "_show_message_box",
                                    Qt.QueuedConnection,
                                    Q_ARG(str, title),
                                    Q_ARG(str, msg),
                                    Q_ARG(int, QMessageBox.Critical))

    @Slot(str, str, int)
    def _show_message_box(self, title, msg, icon):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(msg)
        box.setIcon(icon)
        box.exec()