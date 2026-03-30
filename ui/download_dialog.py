import os
import uuid
import requests

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox
)

from core.video_info import VideoInfo
from core.utils import resource_path
from ui.components.thumbnail_widget import ThumbnailWidget
from models.download_item import DownloadItem


PLACEHOLDER = resource_path("assets/placeholder.png")


class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Novo Download")
        self.setMinimumSize(500, 500)

        self.video_info = None
        self.download_item = None
        self.thumbnail_path = None

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
        self.url_input.setPlaceholderText("Cole o link e pressione ENTER")
        self.url_input.returnPressed.connect(self._load_video_info)
        layout.addWidget(self.url_input)

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

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)

        ok_button = QPushButton("Adicionar")
        ok_button.clicked.connect(self._confirm)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

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

        try:
            info = VideoInfo().extract(url)
            self.video_info = info

            # thumbnail único
            thumb_url = info.get("thumbnail")
            if thumb_url:
                os.makedirs("temp", exist_ok=True)

                self.thumbnail_path = f"temp/{uuid.uuid4()}.jpg"

                r = requests.get(thumb_url, timeout=10)
                with open(self.thumbnail_path, "wb") as f:
                    f.write(r.content)

                self.thumbnail.set_thumbnail(self.thumbnail_path)

            # auto nome
            title = info.get("title", "")
            if title:
                self.filename_input.setText(title)

        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    def _confirm(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()

        if not url or not path:
            QMessageBox.warning(self, "Erro", "URL ou pasta inválida")
            return

        if not self.video_info:
            QMessageBox.warning(self, "Erro", "Carregue o vídeo primeiro (ENTER)")
            return

        filename = self.filename_input.text().strip()

        self.download_item = DownloadItem(
            url=url,
            title=filename if filename else self.video_info.get("title", "Sem título"),
            format_type=self.format_selector.currentText(),
            quality=self.quality_selector.currentText(),
            thumbnail=self.thumbnail_path or "",
            status="pending",
        )

        self.download_item.output_path = path

        self.accept()

    def get_result(self):
        return self.download_item