# ui/components/download_card.py

""" Here you will find:
    - content car UI componente implementation;
    - all the functions here will work to add UI inputs 
    and visual feedback to each Download card showed on
    history at main window.
"""

import os
import subprocess

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from core.i18n import tr, SUPPORTED_LANGUAGES

# progress bar colors: download (green) and conversion/cut after download (blue)
DOWNLOAD_BAR_STYLE = "QProgressBar::chunk { background-color: #4CAF50; }"
CONVERSION_BAR_STYLE = "QProgressBar::chunk { background-color: #2196F3; }"

# estimated time left to friendly text (None or negative = still calculating)
def format_remaining(seconds):
    if seconds is None or seconds < 0:
        return tr("card.calculating_time")
    seconds = int(seconds)
    if seconds < 60:
        return tr("card.seconds_left", seconds=seconds)
    if seconds < 3600:
        return tr("card.minutes_left", minutes=round(seconds / 60))
    h, rest = divmod(seconds, 3600)
    return tr("card.hours_left", hours=h, minutes=f"{rest // 60:02d}")

""" The quality label is saved on history.json in the language the app had
    when the download was made. Playlist items save a text label, so it's
    shown again in the current language, whatever language saved it.
"""
_BEST_QUALITY_LABELS = {"best"} | {
    tr("playlist.best_quality_label", lang=code) for code in SUPPORTED_LANGUAGES
}

# Download Card component class
class DownloadCard(QWidget):
    def __init__(self, item):
        super().__init__()

        self.item = item
        self.on_cancel = None
        self.on_retry = None
        self.on_copy = None
        self.on_remove = None
        # None while downloading, "convert"/"cut" while ffmpeg processes the file
        self._phase = None

        # status visual feedback is disconect to real status to doesn't make wrogn changes
        self._terminal_view = item.status in ("completed", "error", "cancelled")

        self._setup_ui()
        self._apply_status()


    """ ====================
        UI IMPLEMENTATION 
      =================== """
    def _setup_ui(self):
        # set fixed card size
        self.setFixedHeight(170)
        self.setMinimumHeight(170)
        self.setMaximumHeight(170)

        # main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(10)

        # ========== LEFT COLUMN: THUMBNAIL ==========
        self.thumbnail_label = QLabel()
        # set thumbnail fixed size
        self.thumbnail_label.setFixedSize(220, 150)
        self.thumbnail_label.setStyleSheet("border: 1px solid #444; background-color: #2a2a2a; border-radius: 4px;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("🎬")
        self._load_thumbnail()
        main_layout.addWidget(self.thumbnail_label)

        # ========== CENTER COLUMN: INFORMATIONS ==========
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(4)

        # salved file name - main info
        self.title_label = QLabel(self.item.title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.title_label.setWordWrap(True)
        center_layout.addWidget(self.title_label)

        # original video name - secundary info
        orig_text = tr("card.original", title=self.item.original_title)
        self.custom_name_label = QLabel(orig_text)
        self.custom_name_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.custom_name_label.setWordWrap(True)
        center_layout.addWidget(self.custom_name_label)

        # card info: format + quality + size
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("color: #888; font-size: 11px;")
        center_layout.addWidget(self.meta_label)

        # progress container - only visible while downloading
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet(DOWNLOAD_BAR_STYLE)
        progress_layout.addWidget(self.progress_bar)
        self.progress_container.hide()
        center_layout.addWidget(self.progress_container)

        # text status - visible when isn't downloading
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #ccc; font-size: 11px;")
        center_layout.addWidget(self.status_label)

        main_layout.addWidget(center_widget, stretch=1)

        # ========== RIGHT COLUMN: INDICATORS AND BUTTONS ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # status indicator - color dot feedback
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet("border-radius: 6px; background-color: #888;")
        right_layout.addWidget(self.status_dot, alignment=Qt.AlignRight)

        #  ================= MAIN AREA - changes by diferent states ===================
        # while downloafing
        self.download_buttons = QWidget()
        download_btns_layout = QVBoxLayout(self.download_buttons)
        download_btns_layout.setContentsMargins(0, 0, 0, 0)
        download_btns_layout.setSpacing(4)
        self.cancel_btn = QPushButton(tr("common.cancel"))
        self.cancel_btn.clicked.connect(self._cancel_download)
        download_btns_layout.addWidget(self.cancel_btn)
        self.download_buttons.hide()
        right_layout.addWidget(self.download_buttons)

        # after complete download
        self.action_buttons = QWidget()
        action_btns_layout = QVBoxLayout(self.action_buttons)
        action_btns_layout.setContentsMargins(0, 0, 0, 0)
        action_btns_layout.setSpacing(4)
        self.open_file_btn = QPushButton(tr("card.open_file"))
        self.open_file_btn.clicked.connect(self._open_file)
        self.open_folder_btn = QPushButton(tr("card.open_folder"))
        self.open_folder_btn.clicked.connect(self._open_folder)
        action_btns_layout.addWidget(self.open_file_btn)
        action_btns_layout.addWidget(self.open_folder_btn)
        self.action_buttons.hide()
        right_layout.addWidget(self.action_buttons)

        # "try again" button - when fail or canceled
        self.retry_btn = QPushButton(tr("card.retry"))
        self.retry_btn.clicked.connect(self._retry_download)
        self.retry_btn.hide()
        right_layout.addWidget(self.retry_btn)

        right_layout.addStretch()

        # ===== Secundary row: copy link + remove buttons =====
        secondary_row = QHBoxLayout()
        secondary_row.setContentsMargins(0, 0, 0, 0)
        secondary_row.setSpacing(4)
        self.copy_link_btn = QPushButton(tr("card.copy_link"))
        self.copy_link_btn.setObjectName("secondaryBtn")
        self.copy_link_btn.clicked.connect(self._copy_link)
        self.remove_btn = QPushButton(tr("card.remove"))
        self.remove_btn.setObjectName("removeBtn")
        self.remove_btn.clicked.connect(self._remove_card)
        secondary_row.addWidget(self.copy_link_btn)
        secondary_row.addWidget(self.remove_btn)
        right_layout.addLayout(secondary_row)

        main_layout.addWidget(right_widget)

        # card general style
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
                padding: 7px 12px;
                color: #eee;
                min-width: 115px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                color: #666;
            }
            QPushButton#secondaryBtn, QPushButton#removeBtn {
                padding: 5px 8px;
                min-width: 0px;
                font-size: 11px;
            }
            QPushButton#removeBtn:hover {
                background-color: #5a2a2a;
                border-color: #a33;
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


    """ ===================
        LOAD THUMBNAIL
      =================== """
    # load thumbnail image to UI
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


    """ =====================
        VIDEO INFO LOADING
      ===================== """
    # set card info - quality, size, etc.
    def _update_meta_info(self):
        # quality info
        quality_text = getattr(self.item, 'quality', 'Auto')
        if quality_text in _BEST_QUALITY_LABELS:
            quality_text = tr("playlist.best_quality_label")
        format_type = getattr(self.item, 'format_type', 'MP4')

        # file size info
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

        # set info into UI 
        self.meta_label.setText(f"{format_type} • {quality_text}{size_text}")


    """ ==========================
        DYNAMIC LAYOUT AND STATUS
      ========================== """
    # set feedback status
    def _apply_status(self):
        status = self.item.status

        # status dictionary 
        status_map = {
            "queued":      ("#607D8B", tr("card.status_queued")),
            "downloading": ("#FFC107", tr("card.status_downloading")),
            "completed":   ("#4CAF50", tr("card.status_completed")),
            "error":       ("#F44336", tr("card.status_error")),
            "cancelled":   ("#9E9E9E", tr("card.status_cancelled"))
        }
        color, text = status_map.get(status, ("#9E9E9E", status))

        # any status change leaves the conversion mode (a retry starts green again)
        if self._phase is not None:
            self._phase = None
            self.progress_bar.setStyleSheet(DOWNLOAD_BAR_STYLE)
        self.status_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        self.status_label.setText(text)

        # in case card state is downloading or queued
        if status in ("downloading", "queued"):
            # both states allow cancell
            self.download_buttons.show()
            self.action_buttons.hide()
            self.retry_btn.hide()
            self.cancel_btn.setEnabled(True)
            # if is downloading show the progress bar, else return a waiting queue feedback
            if status == "downloading":
                self.progress_container.show()
                self.status_label.hide()
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setFormat("%p%")
            else: 
                self.progress_container.hide()
                self.status_label.show()
        # in case card state is complete, fail or cancelled
        else:
            self.progress_container.hide()
            self.status_label.show()
            self.download_buttons.hide()
            if status == "completed":
                # complete: draw open file and open file_folder buttons
                self.action_buttons.show()
                self.open_file_btn.setEnabled(True)
                self.open_folder_btn.setEnabled(True)
                self.retry_btn.hide()
            elif status == "error":
                # fail: just "try again" button
                self.action_buttons.hide()
                self.retry_btn.show()
            # if was cancelled
            else:
                self.action_buttons.hide()
                self.retry_btn.hide()

        # reload card info
        self._update_meta_info()


    """ =====================
        PUBLIC FUNCTIONS
      ===================== """
    # progress bar updater
    def update_progress(self, value):
        # the conversion/cut has its own progress (see update_conversion)
        if self._phase is not None:
            return
        value = max(0, min(100, value))
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value}%")

    """ Conversion / cut progress, after the download finishes.
        Uses the same progress bar (same place, same card size), blue colored.
        percent -1 = unknown duration (busy bar), seconds_left -1 = calculating.
    """
    def update_conversion(self, kind, percent, seconds_left):
        # first call: enter conversion mode
        if self._phase != kind:
            self._phase = kind
            self.progress_bar.setStyleSheet(CONVERSION_BAR_STYLE)

        action = tr("card.cutting") if kind == "cut" else tr("card.converting")

        if percent < 0:
            # unknown duration: "busy" animation, no percent and no time
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat(action)
            return

        percent = max(0, min(100, percent))
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        # "%" is special on QProgressBar format (%p, %v), "%%" is a literal "%"
        self.progress_bar.setFormat(
            f"{action} {percent}%% • {format_remaining(seconds_left)}"
        )

    # card updade estatus
    def update_status(self, status):
        self.item.status = status
        self._terminal_view = status in ("completed", "error", "cancelled")
        self._apply_status()

    # sincronize UI and thread process status in real time
    def mark_downloading(self):
        if self._terminal_view:
            return
        if self.item.status != "downloading" or not self.progress_container.isVisibleTo(self):
            self.item.status = "downloading"
            self._apply_status()


    """ ==================
        BUTTON ACTIONS
      ================= """
    # there's no necessary comment nothing about
    
    def _cancel_download(self):
        if self.on_cancel:
            self.on_cancel()
        self.cancel_btn.setEnabled(False)
        self.status_label.setText(tr("card.cancelling"))

    def _retry_download(self):
        if self.on_retry:
            self.retry_btn.hide()
            self.on_retry()

    def _remove_card(self):
        if self.on_remove:
            self.on_remove()

    def _copy_link(self):
        from PySide6.QtWidgets import QApplication
        url = getattr(self.item, "url", "") or ""
        if self.on_copy:
            self.on_copy()
        elif url:
            QApplication.clipboard().setText(url)
        # fast feedback
        self.copy_link_btn.setText(tr("card.link_copied"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_link_btn.setText(tr("card.copy_link")))

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