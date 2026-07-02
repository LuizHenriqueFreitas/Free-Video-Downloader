import os
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit, QFileDialog, QMessageBox,
    QCheckBox)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QSize
from PySide6.QtGui import QPixmap

from models.download_item import DownloadItem
from core.utils import resolve_unique_title, safe_filename
from storage.settings_store import SettingsStore


def _fmt_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f" [{h}:{m:02d}:{s:02d}]"
    return f" [{m:02d}:{s:02d}]"


class ThumbnailLoader(QObject):
    """Carrega thumbnail em thread separada"""
    loaded = Signal(int, QPixmap)  # index, pixmap
    finished = Signal()

    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def run(self):
        for idx, entry in enumerate(self.entries):
            thumb_url = entry.get("thumbnail")
            if thumb_url:
                try:
                    r = requests.get(thumb_url, timeout=5)
                    if r.status_code == 200:
                        pixmap = QPixmap()
                        pixmap.loadFromData(r.content)
                        scaled = pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.loaded.emit(idx, scaled)
                except Exception:
                    pass
        self.finished.emit()


class PlaylistDialog(QDialog):
    """
    Mostra os vídeos de uma playlist com checkboxes para o usuário
    escolher quais baixar. Compartilha formato e pasta de destino.
    """

    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.entries = playlist.get("entries", [])
        self._items = []
        self.settings = SettingsStore()
        self._thumbnails = {}  # index -> QPixmap

        self.setWindowTitle("Baixar playlist")
        self.setMinimumSize(700, 600)

        self._setup_ui()
        self._load_thumbnails()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = self.playlist.get("title", "Playlist")
        header = QLabel(f"Playlist: {title}  ({len(self.entries)} vídeos)")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        # seleção
        sel_bar = QHBoxLayout()
        select_all = QPushButton("Selecionar todos")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton("Limpar seleção")
        clear_all.clicked.connect(lambda: self._set_all(False))
        sel_bar.addWidget(select_all)
        sel_bar.addWidget(clear_all)
        sel_bar.addStretch()
        layout.addLayout(sel_bar)

        # lista com thumbnail
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(80, 60))
        for entry in self.entries:
            label = (entry.get("title") or "(sem título)") + _fmt_duration(entry.get("duration"))
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # formato
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Formato:"))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        fmt_layout.addWidget(self.format_selector)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # aviso de qualidade
        self.quality_warning = QLabel(
            "ℹ️ Os vídeos serão baixados na MELHOR QUALIDADE disponível (máx. 1080p) "
            "com os nomes originais do YouTube."
        )
        self.quality_warning.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background: #f0f0f0; border-radius: 4px;")
        self.quality_warning.setWordWrap(True)
        layout.addWidget(self.quality_warning)

        # pasta
        layout.addWidget(QLabel("Pasta de destino:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton("Escolher pasta")
        path_button.clicked.connect(self._choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)

        # botões
        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Baixar selecionados")
        ok.clicked.connect(self._confirm)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    def _load_thumbnails(self):
        """Carrega thumbnails em background"""
        self._thumb_thread = QThread()
        self._thumb_worker = ThumbnailLoader(self.entries)
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_thread.started.connect(self._thumb_worker.run)
        self._thumb_worker.loaded.connect(self._on_thumb_loaded)
        self._thumb_worker.finished.connect(self._thumb_thread.quit)
        self._thumb_thread.finished.connect(self._thumb_thread.deleteLater)
        self._thumb_thread.start()

    def _on_thumb_loaded(self, index, pixmap):
        """Aplica thumbnail ao item da lista"""
        if index < self.list_widget.count():
            item = self.list_widget.item(index)
            item.setIcon(pixmap)

    def _set_all(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

    def _show_playlist_warning(self):
        """Mostra aviso sobre qualidade 1080p (opção 'não mostrar novamente')"""
        if self.settings.get_skip_playlist_warning():
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle("Download da playlist")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            "📋 **Atenção ao baixar a playlist**\n\n"
            "• Todos os vídeos serão baixados na **melhor qualidade disponível até 1080p**\n"
            "• Os nomes originais do YouTube serão preservados\n"
            "• Vídeos em 4K/8K serão convertidos para 1080p para economizar espaço\n\n"
            "Deseja continuar?"
        )
        
        dont_ask = QCheckBox("Não mostrar esta mensagem novamente")
        msg.setCheckBox(dont_ask)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        result = msg.exec()
        
        if dont_ask.isChecked():
            self.settings.set_skip_playlist_warning(True)
        
        return result == QMessageBox.Yes

    def _confirm(self):
        folder = self.path_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Erro", "Escolha a pasta de destino.")
            return

        fmt = self.format_selector.currentText()
        selected = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                entry = it.data(Qt.UserRole)
                if entry.get("url"):
                    selected.append(entry)

        if not selected:
            QMessageBox.warning(self, "Erro", "Selecione ao menos um vídeo.")
            return

        # Aviso de qualidade 1080p
        if not self._show_playlist_warning():
            return

        # QUALIDADE LIMITADA A 1080P
        # Força quality_id = None mas o download_worker usará bestvideo[height<=1080]
        # Isso é controlado no momento da criação do DownloadItem
        
        used_titles = set()
        items = []
        for entry in selected:
            base_title = entry.get("title") or "video"
            title = resolve_unique_title(folder, base_title, fmt)
            while title in used_titles:
                title = resolve_unique_title(folder, title + " ", fmt)
            used_titles.add(title)

            # QUALITY_ID FORÇADO para 1080p máximo
            # Se for MP4, usa formato com limitação de altura
            quality_id = None
            if fmt == "MP4":
                quality_id = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

            items.append(DownloadItem(
                url=entry["url"],
                title=title,
                original_title=base_title,
                format_type=fmt,
                quality="Melhor qualidade (até 1080p)",
                quality_id=quality_id,
                thumbnail=entry.get("thumbnail"),
                status="pending",
                output_path=folder,
            ))

        self._items = items
        self.accept()

    def get_result(self):
        return self._items