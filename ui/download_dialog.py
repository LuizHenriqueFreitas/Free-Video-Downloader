import os
import requests
from uuid import uuid4

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import QTimer, QThread, QObject, Signal

from core.video_info import VideoInfo
from core.utils import resource_path, cookies_exists
from ui.components.thumbnail_widget import ThumbnailWidget
from models.download_item import DownloadItem


PLACEHOLDER = resource_path("assets/placeholder.png")


# ==========================
# WORKER (THREAD SAFE)
# ==========================
class VideoInfoWorker(QObject):
    finished = Signal(dict, str)  # info, thumb_path
    error = Signal(str)

    def __init__(self, url, temp_path):
        super().__init__()
        self.url = url
        self.temp_path = temp_path

    def run(self):
        try:
            info = VideoInfo().extract(self.url)

            thumb_url = info.get("thumbnail")
            thumb_path = None

            if thumb_url:
                os.makedirs("temp", exist_ok=True)

                r = requests.get(thumb_url, timeout=10)
                thumb_path = self.temp_path

                with open(thumb_path, "wb") as f:
                    f.write(r.content)

            self.finished.emit(info, thumb_path)

        except Exception as e:
            self.error.emit(str(e))


# ==========================
# DIALOG
# ==========================
class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Novo Download")
        self.setMinimumSize(500, 550)

        self.video_info = None
        self.download_item = None

        # controle de requisição
        self._current_request_id = None
        self._thread = None
        self._worker = None
        self._current_thumb_path = None

        # debounce
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._load_video_info)

        self._setup_ui()

    # ==========================
    # UI
    # ==========================
    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # URL
        layout.addWidget(QLabel("URL do vídeo:"))
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self._on_url_changed)
        layout.addWidget(self.url_input)

        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Thumbnail
        self.thumbnail = ThumbnailWidget(PLACEHOLDER)
        layout.addWidget(self.thumbnail)

        # Formato + Qualidade
        format_layout = QHBoxLayout()

        format_layout.addWidget(QLabel("Formato:"))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        self.format_selector.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_selector)

        format_layout.addWidget(QLabel("Qualidade:"))
        self.quality_selector = QComboBox()
        self.quality_selector.setEnabled(False)
        format_layout.addWidget(self.quality_selector)

        layout.addLayout(format_layout)

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

    # ==========================
    # EVENTOS
    # ==========================
    def _on_url_changed(self):
        text = self.url_input.text().strip()

        if "youtube.com" in text or "youtu.be" in text:
            self.status_label.setText("Carregando informações...")
            self.load_timer.start(800)

    def _on_format_changed(self, value):
        if value.upper() == "MP4":
            self.quality_selector.setEnabled(True)
            if self.video_info:
                self._populate_quality_selector()
        else:
            self.quality_selector.clear()
            self.quality_selector.setEnabled(False)

    # ==========================
    # LOAD VIDEO (THREAD SAFE)
    # ==========================
    def _load_video_info(self):
        url = self.url_input.text().strip()

        if not url:
            return

        if not cookies_exists():
            self.status_label.setText("⚠ Cookies não configurados")
            return

        # cancela thread anterior (se existir)
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        request_id = str(uuid4())
        self._current_request_id = request_id

        temp_thumb = os.path.join("temp", f"{request_id}.jpg")
        self._current_thumb_path = temp_thumb

        self.status_label.setText("Carregando...")

        self._thread = QThread()
        self._worker = VideoInfoWorker(url, temp_thumb)

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)

        self._worker.finished.connect(
            lambda info, thumb: self._on_video_loaded(info, thumb, request_id)
        )
        self._worker.error.connect(self._on_video_error)

        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()

    # ==========================
    # HANDLERS
    # ==========================
    def _on_video_loaded(self, info, thumb_path, request_id):
        if request_id != self._current_request_id:
            return

        self.video_info = info

        if thumb_path:
            self.thumbnail.set_thumbnail(thumb_path)

        title = info.get("title", "")
        if title:
            self.filename_input.setText(title)

        self._populate_quality_selector()

        self.status_label.setText("✔ Informações carregadas")

    def _on_video_error(self, msg):
        self.status_label.setText(f"Erro: {msg}")

    # ==========================
    # QUALIDADE
    # ==========================
    def _populate_quality_selector(self):
        if not self.video_info:
            return

        formats = self.video_info.get("formats", [])

        mp4_formats = [
            f for f in formats
            if f.get("ext") == "mp4" and f.get("height")
        ]

        mp4_formats.sort(key=lambda x: x.get("height", 0), reverse=True)

        self.quality_selector.clear()

        for f in mp4_formats:
            label = f"{f.get('height')}p"
            self.quality_selector.addItem(label, f.get("format_id"))

        self.quality_selector.setEnabled(len(mp4_formats) > 0)

    # ==========================
    # AÇÕES
    # ==========================
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

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

        selected_quality_id = None
        if self.format_selector.currentText().upper() == "MP4":
            selected_quality_id = self.quality_selector.currentData()

        self.download_item = DownloadItem(
            url=url,
            title=filename if filename else self.video_info.get("title", "Sem título"),
            format_type=self.format_selector.currentText(),
            quality=self.quality_selector.currentText(),
            quality_id=selected_quality_id,
            thumbnail=self._current_thumb_path,
            status="pending",
        )

        self.download_item.output_path = path

        self.accept()

    def get_result(self):
        return self.download_item