# ui/components/download_card.py

import os
import subprocess

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QFrame
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
    # Altura fixa de 150px
        self.setFixedHeight(150)
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)

        # Layout principal horizontal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)   # reduzido verticalmente
        main_layout.setSpacing(10)

        # ========== COLUNA ESQUERDA: THUMBNAIL ==========
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(220, 150)
        self.thumbnail_label.setStyleSheet("border: 1px solid #444; background-color: #2a2a2a; border-radius: 4px;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("🎬")
        self._load_thumbnail()
        main_layout.addWidget(self.thumbnail_label)

        # ========== COLUNA CENTRAL: INFORMAÇÕES ==========
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(4)

        # Título original (sempre visível)
        self.title_label = QLabel(self.item.original_title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.title_label.setWordWrap(True)
        center_layout.addWidget(self.title_label)

        # Nome do arquivo salvo (se diferente do original ou personalizado)
        if self.item.title != self.item.original_title:
            name_text = f"Salvo como: {self.item.title}"
        else:
            name_text = f"Arquivo: {self.item.title}"
        self.custom_name_label = QLabel(name_text)
        self.custom_name_label.setStyleSheet("color: #aaa; font-size: 11px;")
        center_layout.addWidget(self.custom_name_label)

        # Meta: formato + qualidade + tamanho
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("color: #888; font-size: 11px;")
        center_layout.addWidget(self.meta_label)

        # Container para progresso (aparece apenas durante download)
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        progress_layout.addWidget(self.progress_bar)
        self.progress_container.hide()
        center_layout.addWidget(self.progress_container)

        # Status textual (aparece quando não está baixando)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #ccc; font-size: 11px;")
        center_layout.addWidget(self.status_label)

        main_layout.addWidget(center_widget, stretch=1)

        # ========== COLUNA DIREITA: BOTÕES E INDICADOR ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(8)
        right_layout.setAlignment(Qt.AlignTop)

        # Indicador de status (ponto colorido)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("border-radius: 6px; background-color: #888;")
        right_layout.addWidget(self.status_dot, alignment=Qt.AlignRight)

        # Botões dinâmicos
        self.download_buttons = QWidget()
        download_btns_layout = QVBoxLayout(self.download_buttons)
        download_btns_layout.setSpacing(4)
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self._cancel_download)
        download_btns_layout.addWidget(self.cancel_btn)
        self.download_buttons.hide()
        right_layout.addWidget(self.download_buttons)

        self.action_buttons = QWidget()
        action_btns_layout = QVBoxLayout(self.action_buttons)
        action_btns_layout.setSpacing(4)
        self.open_file_btn = QPushButton("Abrir arquivo")
        self.open_file_btn.clicked.connect(self._open_file)
        self.open_folder_btn = QPushButton("Abrir pasta")
        self.open_folder_btn.clicked.connect(self._open_folder)
        action_btns_layout.addWidget(self.open_file_btn)
        action_btns_layout.addWidget(self.open_folder_btn)
        self.action_buttons.hide()
        right_layout.addWidget(self.action_buttons)

        right_layout.addStretch()
        main_layout.addWidget(right_widget)

        # Estilo geral do card com botões maiores
        self.setStyleSheet("""
            DownloadCard {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #1e1e1e;
                margin-bottom: 8px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
                color: #eee;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                color: #666;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
                color: #eee;
            }
        """)

        self._update_meta_info()

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
                self.thumbnail_label.setText("")
                return
        self.thumbnail_label.setText("🎬")

    # -------------------------
    # META INFOS (qualidade + tamanho)
    # -------------------------
    def _update_meta_info(self):
        quality_text = getattr(self.item, 'quality', 'Auto')
        if quality_text == 'best':
            quality_text = 'Melhor qualidade'
        format_type = getattr(self.item, 'format_type', 'MP4')

        size_text = ""
        if self.item.file_path and os.path.exists(self.item.file_path):
            size_bytes = os.path.getsize(self.item.file_path)
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > 1024:
                size_text = f" • {size_mb/1024:.1f} GB"
            else:
                size_text = f" • {size_mb:.1f} MB"
        elif hasattr(self.item, 'filesize') and self.item.filesize:
            size_bytes = self.item.filesize
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > 1024:
                size_text = f" • {size_mb/1024:.1f} GB"
            else:
                size_text = f" • {size_mb:.1f} MB"

        self.meta_label.setText(f"{format_type} • {quality_text}{size_text}")

    # -------------------------
    # STATUS E LAYOUT DINÂMICO
    # -------------------------
    def _apply_status(self):
        status = self.item.status

        status_map = {
            "queued":      ("#607D8B", "Na fila..."),
            "downloading": ("#FFC107", "Baixando..."),
            "completed":   ("#4CAF50", "Concluído"),
            "error":       ("#F44336", "Falha no download"),
            "cancelled":   ("#9E9E9E", "Cancelado")
        }
        color, text = status_map.get(status, ("#9E9E9E", status))
        self.status_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        self.status_label.setText(text)

        if status == "downloading":
            self.progress_container.show()
            self.status_label.hide()
            self.download_buttons.show()
            self.action_buttons.hide()
            self.cancel_btn.setEnabled(True)
        else:
            self.progress_container.hide()
            self.status_label.show()
            self.download_buttons.hide()
            self.action_buttons.show()
            if status == "completed":
                self.open_file_btn.setEnabled(True)
                self.open_folder_btn.setEnabled(True)
            else:
                self.open_file_btn.setEnabled(False)
                self.open_folder_btn.setEnabled(False)

        self._update_meta_info()

    # -------------------------
    # MÉTODOS PÚBLICOS
    # -------------------------
    def update_progress(self, value):
        value = max(0, min(100, value))
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value}%")

    def update_status(self, status):
        self.item.status = status
        self._apply_status()

    # -------------------------
    # AÇÕES DOS BOTÕES
    # -------------------------
    def _cancel_download(self):
        if self.on_cancel:
            self.on_cancel()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelando...")

    def _open_file(self):
        path = self.item.file_path
        if path and os.path.exists(path):
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])

    def _open_folder(self):
        path = self.item.file_path
        if path:
            folder = os.path.dirname(path)
            if os.path.exists(folder):
                if os.name == "nt":
                    os.startfile(folder)
                else:
                    subprocess.Popen(["xdg-open", folder])