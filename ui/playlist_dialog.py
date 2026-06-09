# ui/playlist_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal

from models.download_item import DownloadItem
from core.utils import resolve_unique_title
from core.video_info import VideoInfo


# ==========================
# WORKER: carrega a playlist em background
# ==========================
class PlaylistLoadWorker(QObject):
    finished = Signal(object)   # playlist dict ou None
    error = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            playlist = VideoInfo().extract_playlist(self.url)
            self.finished.emit(playlist)
        except Exception as e:
            self.error.emit(str(e))


def _fmt_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f" [{h}:{m:02d}:{s:02d}]"
    return f" [{m:02d}:{s:02d}]"


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

        self.setWindowTitle("Baixar playlist")
        self.setMinimumSize(560, 560)

        self._setup_ui()

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

        # lista
        self.list_widget = QListWidget()
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

    def _set_all(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

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

        # cria os itens; renomeia automaticamente em caso de conflito (bulk)
        used_titles = set()
        items = []
        for entry in selected:
            base_title = entry.get("title") or "video"
            title = resolve_unique_title(folder, base_title, fmt)
            # evita colisão entre itens da própria seleção
            while title in used_titles:
                title = resolve_unique_title(folder, title + " ", fmt)
            used_titles.add(title)

            items.append(DownloadItem(
                url=entry["url"],
                title=title,
                original_title=base_title,
                format_type=fmt,
                quality="Melhor qualidade",
                quality_id=None,
                thumbnail=None,
                status="pending",
                output_path=folder,
            ))

        self._items = items
        self.accept()

    def get_result(self):
        return self._items
