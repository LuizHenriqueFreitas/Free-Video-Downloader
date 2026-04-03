# ui/components/download_card.py

import os
import subprocess

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class DownloadCard(QWidget):
    def __init__(self, item):
        super().__init__()

        self.item = item
        self.on_cancel = None

        self._setup_ui()
        self._apply_status()

    # -------------------------
    # UI
    # -------------------------
    def _setup_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self.setFixedHeight(120)

        # ----------------------
        # THUMBNAIL
        # ----------------------
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setStyleSheet("border: 1px solid #444;")

        self._load_thumbnail()

        main_layout.addWidget(self.thumbnail_label)

        # ----------------------
        # INFO
        # ----------------------
        info_layout = QVBoxLayout()

        self.title_label = QLabel(self.item.title)
        self.title_label.setStyleSheet("font-weight: bold;")
        self.title_label.setWordWrap(True)

        self.meta_label = QLabel(
            f"{self.item.format_type} • {self.item.quality}"
        )
        self.meta_label.setStyleSheet("color: gray;")

        # 🔥 NOVO → status texto
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #BBBBBB; font-size: 11px;")

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.meta_label)
        info_layout.addWidget(self.status_label)

        # ----------------------
        # PROGRESSO
        # ----------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

        info_layout.addWidget(self.progress)

        main_layout.addLayout(info_layout)

        # ----------------------
        # DIREITA
        # ----------------------
        right_layout = QVBoxLayout()

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(14, 14)
        right_layout.addWidget(self.status_dot, alignment=Qt.AlignRight)

        self.open_btn = QPushButton("Abrir")
        self.open_btn.clicked.connect(self._open_file)
        right_layout.addWidget(self.open_btn)

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self._cancel_download)
        right_layout.addWidget(self.cancel_btn)

        right_layout.addStretch()
        main_layout.addLayout(right_layout)

        self.setStyleSheet("""
            QWidget {
                border: 1px solid #333;
                border-radius: 8px;
                padding: 8px;
                background-color: #1e1e1e;
            }
        """)

    # -------------------------
    # THUMBNAIL
    # -------------------------
    def _load_thumbnail(self):
        if self.item.thumbnail and os.path.exists(self.item.thumbnail):
            pixmap = QPixmap(self.item.thumbnail)

            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(
                    pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )
                return

        # fallback
        self.thumbnail_label.setText("Sem imagem")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)

    # -------------------------
    # STATUS
    # -------------------------
    def _apply_status(self):
        status = self.item.status

        color = "#9E9E9E"
        text = ""

        if status == "queued":
            color = "#607D8B"
            text = "Na fila..."

        elif status == "downloading":
            color = "#FFC107"
            text = "Baixando..."

        elif status == "completed":
            color = "#4CAF50"
            text = "Concluído"

        elif status == "error":
            color = "#F44336"
            text = "Erro"

        elif status == "cancelled":
            color = "#9E9E9E"
            text = "Cancelado"

        self.status_label.setText(text)

        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 7px;
        """)

        # comportamento
        if status == "queued":
            self.progress.setVisible(False)
            self.cancel_btn.setEnabled(True)
            self.open_btn.setEnabled(False)

        elif status == "downloading":
            self.progress.setVisible(True)
            self.cancel_btn.setEnabled(True)
            self.open_btn.setEnabled(False)

        elif status == "completed":
            self.progress.setVisible(False)
            self.cancel_btn.setEnabled(False)
            self.open_btn.setEnabled(True)

        else:
            self.progress.setVisible(False)
            self.cancel_btn.setEnabled(False)
            self.open_btn.setEnabled(False)

    # -------------------------
    # AÇÕES
    # -------------------------
    def update_progress(self, value):
        # proteção extra
        value = max(0, min(100, value))
        self.progress.setValue(value)

    def update_status(self, status):
        self.item.status = status
        self._apply_status()

    def _cancel_download(self):
        if self.on_cancel:
            self.on_cancel()

    def _open_file(self):
        path = self.item.file_path

        if path and os.path.exists(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])