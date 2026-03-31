# ui/download_dialog.py

import os
import requests

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QTimer

from core.video_info import VideoInfo
from core.utils import resource_path, cookies_exists
from ui.components.thumbnail_widget import ThumbnailWidget
from models.download_item import DownloadItem


TEMP_THUMBNAIL = "temp/thumbnail.jpg"
PLACEHOLDER = resource_path("assets/placeholder.png")


class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Novo Download")
        self.setMinimumSize(500, 500)

        self.video_info = None
        self.download_item = None

        # debounce timer
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._load_video_info)

        self._setup_ui()

    # -------------------------
    # UI
    # -------------------------

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # URL
        layout.addWidget(QLabel("URL do vídeo:"))
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self._on_url_changed)
        layout.addWidget(self.url_input)

        # Status (feedback UX)
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Thumbnail
        self.thumbnail = ThumbnailWidget(PLACEHOLDER)
        layout.addWidget(self.thumbnail)

        # Formato
        layout.addWidget(QLabel("Formato:"))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        layout.addWidget(self.format_selector)

        # Qualidade
        layout.addWidget(QLabel("Qualidade:"))
        self.quality_selector = QComboBox()
        self.quality_selector.addItems(["Máxima", "Full HD"])
        layout.addWidget(self.quality_selector)

        # Pasta
        layout.addWidget(QLabel("Pasta de destino:"))
        path_layout = QHBoxLayout()

        self.path_input = QLineEdit()
        path_button = QPushButton("Escolher pasta")
        path_button.clicked.connect(self._choose_folder)

        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)

        layout.addLayout(path_layout)

        # Nome
        layout.addWidget(QLabel("Nome do arquivo (opcional):"))
        self.filename_input = QLineEdit()
        layout.addWidget(self.filename_input)

        # Botões
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        self.ok_button = QPushButton("Adicionar")
        self.ok_button.clicked.connect(self._confirm)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

    # -------------------------
    # EVENTOS
    # -------------------------

    def _on_url_changed(self):
        text = self.url_input.text().strip()

        # evita chamadas desnecessárias
        if "youtube.com" in text or "youtu.be" in text:
            self.status_label.setText("Carregando informações...")
            self.load_timer.start(800)

    # -------------------------
    # AÇÕES
    # -------------------------

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

    def _load_video_info(self):
        url = self.url_input.text().strip()

        if not url:
            return

        if not cookies_exists():
            self.status_label.setText("⚠ Cookies não configurados")
            return

        try:
            info = VideoInfo().extract(url)
            self.video_info = info

            # thumbnail
            thumb_url = info.get("thumbnail")
            if thumb_url:
                os.makedirs("temp", exist_ok=True)

                r = requests.get(thumb_url, timeout=10)
                with open(TEMP_THUMBNAIL, "wb") as f:
                    f.write(r.content)

                self.thumbnail.set_thumbnail(TEMP_THUMBNAIL)

            # nome automático
            title = info.get("title", "")
            if title:
                self.filename_input.setText(title)

            self.status_label.setText("✔ Informações carregadas")

        except Exception as e:
            self.status_label.setText(f"Erro: {str(e)}")

    def _confirm(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()

        if not url or not path:
            QMessageBox.warning(self, "Erro", "URL ou pasta inválida")
            return

        if not self.video_info:
            QMessageBox.warning(self, "Erro", "Carregue as informações do vídeo primeiro")
            return

        filename = self.filename_input.text().strip()

        self.download_item = DownloadItem(
            url=url,
            title=filename if filename else self.video_info.get("title", "Sem título"),
            format_type=self.format_selector.currentText(),
            quality=self.quality_selector.currentText(),
            thumbnail=TEMP_THUMBNAIL,
            status="pending",
        )

        self.download_item.output_path = path

        self.accept()

    def get_result(self):
        return self.download_item