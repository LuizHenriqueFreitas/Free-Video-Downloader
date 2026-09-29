# ui/playlist_dialog.py

""" Playlist download logic and guideline:
    When user want to made a playlist download, is possible 
    select wished videos, but all videos can only be download 
    on 1080p or best quality availabe (if doens't exist 1080p
    availabe). 
    
    That's a default and imutable setting. 

    Also the destine folder will be the same for all videos from
    that playlist.

    We decide to make the quality unique and apply to all playlist
    content witout user fine-tuning because the idea is build a 
    simpler, more stable version that meets most needs.
"""

""" Here you will find:
    - Playlist setting download dialog;
    - playlist videos thumbnail loader;
    - playlist dialog events function - like ui buttons;
    - playlists user warning text boxes;
    - playlist confirm download;
"""

import os
from uuid import uuid4
import requests
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit, QFileDialog, QMessageBox,
    QCheckBox)
from PySide6.QtCore import Qt, QThread, QObject, Signal, QSize
from PySide6.QtGui import QPixmap

from core.i18n import tr
from models.download_item import DownloadItem
from core.utils import resolve_unique_title, get_thumbnails_dir
from storage.settings_store import SettingsStore


# calculate video duration to show in UI
def _fmt_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f" [{h}:{m:02d}:{s:02d}]"
    return f" [{m:02d}:{s:02d}]"


""" ==============================
    THUMBNAIL LOADER

    maybe that should be on a separete file
================================= """
# load the thumbnaol at a separete thread
class ThumbnailLoader(QObject):
    # index, preview icon, local file path (saved to disk so it survives into
    # the download history — entry["thumbnail"] is just a remote URL and
    # DownloadCard can only render a local file)
    loaded = Signal(int, QPixmap, str)
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
                        if not pixmap.isNull():
                            video_id = entry.get("id") or str(uuid4())
                            local_path = os.path.join(get_thumbnails_dir(), f"{video_id}.jpg")
                            try:
                                with open(local_path, "wb") as f:
                                    f.write(r.content)
                            except OSError:
                                local_path = ""
                            scaled = pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.loaded.emit(idx, scaled, local_path)
                except Exception:
                    pass
        self.finished.emit()


""" ==========================
        PLAYLIST DIALOG
  ========================= """
# show the playlist vídeos with checkboxest o user select wich one will be downloaded
# all videos select will share same format (.mp4 or .mp3) and save destine folder
class PlaylistDialog(QDialog):
    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.entries = playlist.get("entries", [])
        self._items = []
        self.settings = SettingsStore()
        self._thumbnails = {}
        self.setWindowTitle(tr("playlist.title"))
        self.setMinimumSize(700, 600)

        self._setup_ui()
        self._load_thumbnails()

    # UI implementation
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = self.playlist.get("title", "Playlist")
        header = QLabel(tr("playlist.header", title=title, count=len(self.entries)))
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        # selection
        sel_bar = QHBoxLayout()
        select_all = QPushButton(tr("playlist.select_all"))
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton(tr("playlist.clear_selection"))
        clear_all.clicked.connect(lambda: self._set_all(False))
        sel_bar.addWidget(select_all)
        sel_bar.addWidget(clear_all)
        sel_bar.addStretch()
        layout.addLayout(sel_bar)

        # list with thumbnails
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(80, 60))
        for entry in self.entries:
            label = (entry.get("title") or tr("common.untitled_entry")) + _fmt_duration(entry.get("duration"))
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, entry)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # format selection
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel(tr("common.format")))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        fmt_layout.addWidget(self.format_selector)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # quality warning
        self.quality_warning = QLabel(tr("playlist.quality_notice"))
        self.quality_warning.setStyleSheet("color: #666; font-size: 11px; padding: 5px; background: #f0f0f0; border-radius: 4px;")
        self.quality_warning.setWordWrap(True)
        layout.addWidget(self.quality_warning)

        # select destine folder
        layout.addWidget(QLabel(tr("common.destination_folder")))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton(tr("common.choose_folder"))
        path_button.clicked.connect(self._choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)

        # action buttons
        btns = QHBoxLayout()
        cancel = QPushButton(tr("common.cancel"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("playlist.download_selected"))
        ok.clicked.connect(self._confirm)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        layout.addLayout(btns)

    # load thumbnails on background
    def _load_thumbnails(self):
        self._thumb_thread = QThread()
        self._thumb_worker = ThumbnailLoader(self.entries)
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_thread.started.connect(self._thumb_worker.run)
        self._thumb_worker.loaded.connect(self._on_thumb_loaded)
        self._thumb_worker.finished.connect(self._thumb_thread.quit)
        self._thumb_thread.finished.connect(self._thumb_thread.deleteLater)
        self._thumb_thread.start()

    # add thumbnail to list when load finished
    def _on_thumb_loaded(self, index, pixmap, local_path):
        if index < self.list_widget.count():
            item = self.list_widget.item(index)
            item.setIcon(pixmap)
        if local_path:
            self._thumbnails[index] = local_path

    # select all button - set all itens as checked
    def _set_all(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(state)

    # choose folder button
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("common.choose_folder"))
        if folder:
            self.path_input.setText(folder)

    # show quality warning to user - allow deactivate the warning by checkbox
    def _show_playlist_warning(self):
        if self.settings.get_skip_playlist_warning():
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("playlist.warning_title"))
        msg.setIcon(QMessageBox.Information)
        msg.setText(tr("playlist.warning_text"))

        dont_ask = QCheckBox(tr("common.dont_show_again"))
        msg.setCheckBox(dont_ask)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        result = msg.exec()
        
        if dont_ask.isChecked():
            self.settings.set_skip_playlist_warning(True)
        
        return result == QMessageBox.Yes

    # confirm playlist download order
    def _confirm(self):
        folder = self.path_input.text().strip()
        if not folder:
            QMessageBox.warning(self, tr("common.error"), tr("playlist.choose_folder_first"))
            return

        fmt = self.format_selector.currentText()
        selected = []
        # add each selected video url to a list (keep its list index, so we
        # can later match it back to the thumbnail already downloaded by
        # ThumbnailLoader for that same row)
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                entry = it.data(Qt.UserRole)
                if entry.get("url"):
                    selected.append((i, entry))

        # check if leastways one was selected
        if not selected:
            QMessageBox.warning(self, tr("common.error"), tr("playlist.select_at_least_one"))
            return

        # show quality warning
        if not self._show_playlist_warning():
            return

        used_titles = set()
        items = []
        for index, entry in selected:
            base_title = entry.get("title") or "video"
            # used_titles: names of the videos above in this same playlist, so two videos
            # with the same title (ex.: "[Private video]") get "title" and "title (1)"
            title = resolve_unique_title(folder, base_title, fmt, reserved=used_titles)
            used_titles.add(title)

            quality_id = None
            if fmt == "MP4":
                quality_id = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

            # add videos to be downloaded by items list
            # thumbnail here must be a local file: DownloadCard reads it with
            # os.path.exists()/QPixmap, entry["thumbnail"] is just a remote URL
            items.append(DownloadItem(
                url=entry["url"],
                title=title,
                original_title=base_title,
                format_type=fmt,
                quality=tr("playlist.best_quality_label"),
                quality_id=quality_id,
                thumbnail=self._thumbnails.get(index),
                status="pending",
                output_path=folder,
            ))

        self._items = items
        self.accept()

    # return the selected videos from playlist to be downloaded
    def get_result(self):
        return self._items