# ui/main_window.py

import os
import shutil

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QMessageBox, QFileDialog, QLabel
)

from controllers.download_controller import DownloadController
from services.download_service import DownloadService
from services.updater import check_and_update, get_installed_version

from ui.components.download_card import DownloadCard
from ui.download_dialog import DownloadDialog

from core.utils import get_cookies_path, cookies_exists


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

        # Top bar
        top_bar = QHBoxLayout()

        self.new_button = QPushButton("+ Colar link")
        self.new_button.clicked.connect(self._open_download_dialog)

        self.update_button = QPushButton("Atualizar yt-dlp")
        self.update_button.clicked.connect(self._update_ytdlp)

        self.import_cookies_btn = QPushButton("Importar cookies")
        self.import_cookies_btn.clicked.connect(self._import_cookies)

        self.remove_cookies_btn = QPushButton("Remover cookies")
        self.remove_cookies_btn.clicked.connect(self._remove_cookies)

        # 🔥 STATUS VISUAL DOS COOKIES
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

        # Scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    # -------------------------
    # INIT
    # -------------------------

    def _load_version(self):
        version = get_installed_version()
        self.version_label.setText(f"yt-dlp: {version}")

    def _update_ytdlp(self):
        success, msg = check_and_update()
        QMessageBox.information(self, "Atualização", msg)
        self._load_version()

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

            QMessageBox.information(self, "Sucesso", "Cookies importados com sucesso!")
            self._update_cookie_ui()

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def _remove_cookies(self):
        try:
            path = get_cookies_path()

            if os.path.exists(path):
                os.remove(path)
                QMessageBox.information(self, "Removido", "Cookies removidos.")
            else:
                QMessageBox.information(self, "Info", "Nenhum cookie encontrado.")

            self._update_cookie_ui()

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

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
    # DIALOG
    # -------------------------

    def _open_download_dialog(self):
        if not cookies_exists():
            QMessageBox.warning(
                self,
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
    # DOWNLOAD
    # -------------------------

    def _start_download(self, item, card):
        card.update_status("downloading")

        card.on_cancel = lambda: self.download_service.cancel_download(item.id)

        self.download_service.start_download(
            item,
            on_progress=card.update_progress,
            on_finished=self._on_download_finished,
            on_error=self._on_download_error,
            on_cancel=self._on_download_cancelled
        )

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

        QMessageBox.critical(self, "Erro", msg)

    def _on_download_cancelled(self, item):
        card = self.cards.get(item.id)

        if card:
            card.update_status("cancelled")

        self.controller.update_item(item)