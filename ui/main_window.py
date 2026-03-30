from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QMessageBox
)

from controllers.download_controller import DownloadController
from services.download_service import DownloadService
from services.updater import check_and_update, get_installed_version

from ui.components.download_card import DownloadCard
from ui.download_dialog import DownloadDialog


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

        self.version_label = QPushButton("yt-dlp: ...")
        self.version_label.setEnabled(False)

        top_bar.addWidget(self.new_button)
        top_bar.addWidget(self.update_button)
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
        self.download_service.cleanup(item.id)

    def _on_download_error(self, item, msg):
        card = self.cards.get(item.id)

        if card:
            card.update_status("error")

        self.controller.update_item(item)

        QMessageBox.critical(self, "Erro", msg)

        self.download_service.cleanup(item.id)

    def _on_download_cancelled(self, item):
        card = self.cards.get(item.id)

        if card:
            card.update_status("cancelled")

        self.controller.update_item(item)
        self.download_service.cleanup(item.id)