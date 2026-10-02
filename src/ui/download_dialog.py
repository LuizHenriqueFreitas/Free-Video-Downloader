# ui/download_dialog.py

""" Fix trimmer ui just show when checkbox was clicked - hide by default
"""

""" There're some classes and functions that shouldn't be here, perhaps they should 
    be in their own files.

    We also have some strange logic implementated that needs to be reviewed, 
    understood, and perhaps replaced.
"""

""" Here you will find:
    - load video placeholder asset;
    - all related to this dialog threads set();

    - PlaylistLoadWorker class;
    - VideoInfoWorker Class;

    - DownloadDialog Class;
    - Download dialog UI implementation;
    - event ui changers:
        - url changes;
        - media format download changes;
        - simple / advanced mode changes;

    - playlist_id link extraction;
    - playlist link builder;
    - playlist or unique dialog;

    - load video info into UI;
    - start playlist worker;

    - on_video_loaded() ui print informations;

    - playlist handlers;

    - trimmer tool ui settings;

    - video quality and file size insert into ui information;

    - ui actions logic - like for ui buttons etc;
    - confirm donwload logic;
    
    - memory cleaning functions.
"""

import os
import requests
from uuid import uuid4

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QFileDialog, QMessageBox, QCheckBox,
    QScrollArea, QWidget,
)
from PySide6.QtCore import QTimer, QThread, QObject, Signal, Slot

from core.i18n import tr
from core.video_info import VideoInfo, PreviewDownloader
from services.thread_keeper import keep_thread
from core.utils import (
    resource_path, cookies_exists, looks_like_url,
    is_youtube, is_youtube_playlist,
    file_conflict, resolve_unique_title, expected_output_path,
    safe_filename, invalid_filename_chars, is_valid_filename, get_temp_dir
)
from ui.components.thumbnail_widget import ThumbnailWidget
from ui.audio_language_dialog import AudioLanguageDialog, needs_audio_choice
from models.download_item import DownloadItem
from storage.settings_store import SettingsStore

# load placeholder video image
PLACEHOLDER = resource_path("assets/placeholder.png")

""" Advanced mode (trimmer tool) is turned off for users: still unstable
    (preview player + background threads crashed on some PCs). The code stays
    so it can be studied and turned back on here.
"""
TRIMMER_ENABLED = False

""" Every loading thread is registered with keep_thread() (services/thread_keeper.py):
    it keeps thread + worker alive until the thread really ends, without blocking
    the UI, even if the dialog is closed or another link is pasted meanwhile.
    Never connect deleteLater() on them (see thread_keeper.py).
"""


""" =================================
    PLAYLIST LOADER WORKER CLASS

    Probably is a good idea move that to a own separete file
  ================================= """
class PlaylistLoadWorker(QObject):
    """ Add request_id in the signals so that solt knew witch order response
        without need lambdas with captions (their could cause delivery problems
        with threads at pyside6 and QueueConnection)
    """
    finished = Signal(object, str)
    error = Signal(str, str)

    def __init__(self, url, request_id):
        super().__init__()
        self.url = url
        self.request_id = request_id

    def run(self):
        try:
            playlist = VideoInfo().extract_playlist(self.url)
            self.finished.emit(playlist, self.request_id)
        except Exception as e:
            self.error.emit(str(e), self.request_id)


""" ===========================
    VIDEO INFO WORKER

    Probably is a good idea move that to a own separete file
  ========================== """
class VideoInfoWorker(QObject):
    # info, thumb_path, request_id  (object permite None no thumb)
    finished = Signal(object, object, str)
    error = Signal(str, str)  # msg, request_id

    def __init__(self, url, temp_path, request_id):
        super().__init__()
        self.url = url
        self.temp_path = temp_path
        self.request_id = request_id

    def run(self):
        try:
            info = VideoInfo().extract(self.url)

            thumb_url = info.get("thumbnail")
            thumb_path = None

            if thumb_url:
                r = requests.get(thumb_url, timeout=10)
                thumb_path = self.temp_path
                with open(thumb_path, "wb") as f:
                    f.write(r.content)

            self.finished.emit(info, thumb_path, self.request_id)

        except Exception as e:
            self.error.emit(str(e), self.request_id)


""" ===========================
    PREVIEW WORKER (trimmer tool)

    Probably is a good idea move that to a own separete file
  ========================== """
# downloads a small preview file (video + sound) with yt-dlp on background
class PreviewLoadWorker(QObject):
    # local path (None if it fails), request_id
    finished = Signal(object, str)

    def __init__(self, url, out_dir, name, request_id):
        super().__init__()
        self.url = url
        self.out_dir = out_dir
        self.name = name
        self.request_id = request_id
        self.downloader = PreviewDownloader()

    def run(self):
        path = self.downloader.download(self.url, self.out_dir, self.name)
        self.finished.emit(path, self.request_id)

    # called from the UI thread: kills the yt-dlp process
    def cancel(self):
        self.downloader.cancel()


# remove a file some seconds later: the player may still have it open
# (on Windows an open file can't be deleted). If it still fails, the temp
# folder is wiped on next app start (clear_temp_dir).
def _remove_later(path, delay_ms=1500):
    def _remove():
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    QTimer.singleShot(delay_ms, _remove)


""" ==========================
    DOWNLOAD DIAGLOG CLASS

    main class of this file
  ========================== """
# create a download settings window
class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("dialog.title"))
        self.setMinimumSize(560, 600)

        self.settings = SettingsStore()

        self.video_info = None
        self.download_item = None
        self.trimmer = None
        # items to download - default = 1
        self._results = []

        # requiriments controll
        self._current_request_id = None
        self._thread = None
        self._worker = None
        self._current_thumb_path = None
        self._loading_url = None

        # trimmer preview file (downloaded on background, see PreviewLoadWorker)
        self._preview_worker = None
        self._preview_request_id = None
        self._preview_path = None
        self._preview_url = None

        # conversion warning already shown on this dialog (see _show_conversion_warning)
        self._conversion_warning_shown = False

        # debounce
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._load_video_info)

        self._setup_ui()


    """ ====================
        UI IMPLEMENTATION 
       =================== """
    def _setup_ui(self):
        # responsive window to work on small screens
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.main_layout = layout

        # URL input
        layout.addWidget(QLabel(tr("dialog.url_label")))
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self._on_url_changed)
        layout.addWidget(self.url_input)

        # advanced mode (trimmer) - hide untill get video data
        self.advanced_check = QCheckBox(tr("dialog.advanced_mode"))
        self.advanced_check.setChecked(self.settings.get_advanced_mode())
        self.advanced_check.toggled.connect(self._on_mode_toggled)
        self.advanced_check.hide()
        layout.addWidget(self.advanced_check)

        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Thumbnail - simple mode
        self.thumbnail = ThumbnailWidget(PLACEHOLDER)
        layout.addWidget(self.thumbnail)

        # trimmer container (advanced mode) - draw when load video data
        self.trimmer_container = QVBoxLayout()
        layout.addLayout(self.trimmer_container)

        # selector media extension + quality
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel(tr("common.format")))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        self.format_selector.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_selector)

        format_layout.addWidget(QLabel(tr("dialog.quality")))
        self.quality_selector = QComboBox()
        self.quality_selector.setEnabled(False)
        # "activated" is emitted only by user action (mouse/keyboard), not when
        # the list is filled by code - so the warning never pops up by itself
        self.quality_selector.activated.connect(self._on_quality_activated)
        format_layout.addWidget(self.quality_selector)
        layout.addLayout(format_layout)

        # select final file folder
        layout.addWidget(QLabel(tr("common.destination_folder")))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton(tr("common.choose_folder"))
        path_button.clicked.connect(self._choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)

        # fila saved name - default is the original media title
        layout.addWidget(QLabel(tr("dialog.filename_label")))
        self.filename_input = QLineEdit()
        self.filename_input.textChanged.connect(self._validate_filename_live)
        layout.addWidget(self.filename_input)

        # is that just a visual feedback to warning wrong file names
        self.filename_warning = QLabel("")
        self.filename_warning.setStyleSheet("color: #F44336; font-size: 11px;")
        self.filename_warning.hide()
        layout.addWidget(self.filename_warning)

        # make the windows responsive and scrollable
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # fixed bottom buttons on page footer
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 6, 10, 10)
        self.cancel_button = QPushButton(tr("common.cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = QPushButton(tr("dialog.add"))
        self.ok_button.clicked.connect(self._confirm)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        outer.addLayout(button_layout)

        self._update_mode_visibility()


    """ ========================
                EVENTS
      ======================== """
    # run when a new link is pasted
    def _on_url_changed(self):
        text = self.url_input.text().strip()
        # check if could be a url link
        if looks_like_url(text):
            self.status_label.setText(tr("dialog.loading_info"))
            self.load_timer.start(800)

    # run when user change the media format extension to download - between .mp4 and .mp3
    def _on_format_changed(self, value):
        # mp4: available resolutions to download / mp3: estimated size
        if self.video_info:
            self._populate_quality_selector()
        else:
            self.quality_selector.clear()
            self.quality_selector.setEnabled(False)

    # run when activate or deactivate advanced mode
    def _on_mode_toggled(self, checked):
        self.settings.set_advanced_mode(checked)
        self._update_mode_visibility()
        if checked and self.video_info:
            self._build_trimmer()
        elif not checked:
            self._destroy_trimmer()

    # on advanced mode the trimmer tool replace the simple thumbnail
    def _update_mode_visibility(self):
        advanced = self.advanced_check.isChecked() and self.advanced_check.isVisible()
        self.thumbnail.setVisible(not advanced)
        if self.trimmer:
            self.trimmer.setVisible(advanced)


    """ ======================
          NAME VALIDATION
     ======================= """
    # check if saved file name is allowed
    def _validate_filename_live(self):
        name = self.filename_input.text()
        bad = invalid_filename_chars(name)
        if bad:
            self.filename_warning.setText(tr("dialog.filename_invalid_live", chars="  ".join(bad)))
            self.filename_warning.show()
            self.ok_button.setEnabled(False)
        else:
            self.filename_warning.hide()
            self.ok_button.setEnabled(True)


    """ ===================================
        PLAYLIST DETECTION BY URL

        that probably should be together playlist worker class
      ================================== """
    # extract playlist id from youtube video url (&list=...)
    # need to check queue reprodution links, maybe that logic doens't for that and need to be changed
    def _extract_playlist_id_from_video_url(self, url):
        import re
        match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', url)
        return match.group(1) if match else None

    # True if the url points to a specific video (has a video id), as opposed
    # to a bare playlist link like ".../playlist?list=...".
    def _has_video_id(self, url):
        import re
        return bool(re.search(r'[?&]v=', url))

    # build complete playlist url from ID
    def _build_playlist_url_from_id(self, playlist_id):
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    # question to user if want to download all the playlist or just the link one
    def _ask_single_or_playlist(self, url, playlist_url):
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("dialog.playlist_detected_title"))
        msg.setIcon(QMessageBox.Question)
        msg.setText(tr("dialog.playlist_detected_text"))

        btn_video = msg.addButton(tr("dialog.only_this_video"), QMessageBox.AcceptRole)
        btn_playlist = msg.addButton(tr("dialog.whole_playlist"), QMessageBox.AcceptRole)
        btn_cancel = msg.addButton(tr("common.cancel"), QMessageBox.RejectRole) # why is that off?
        msg.setDefaultButton(btn_video)
        
        msg.exec()

        # send response by clicked button
        clicked = msg.clickedButton()
        if clicked == btn_video:
            return "single"
        elif clicked == btn_playlist:
            return "playlist"
        else:
            return "cancel"


    """ ==========================
        LOADING - THREAD SAFE
      =========================== """
    # load video information to UI
    def _load_video_info(self):
        url = self.url_input.text().strip()
        if not url:
            return

        if not cookies_exists():
            self.status_label.setText(tr("dialog.cookies_not_set"))
            return

        # playlist url detection
        """ is_youtube_playlist() also returns True for a video url that carries
            a "list=" param (see TestIsYoutubePlaylist.test_playlist_query_param),
            so it can't be used here to tell a bare playlist link apart from a
            specific video that just happens to be inside a playlist. That
            distinction is whether the url also carries a video id (v=).
        """
        playlist_id = self._extract_playlist_id_from_video_url(url)
        if playlist_id and self._has_video_id(url):
            playlist_url = self._build_playlist_url_from_id(playlist_id)
            choice = self._ask_single_or_playlist(url, playlist_url)

            if choice == "cancel":
                self.url_input.clear()
                self.status_label.setText(tr("dialog.cancelled_by_user"))
                return
            elif choice == "playlist":
                # same preparation of the normal pipeline below: abandon old request
                # and register this one as the current, otherwise _on_playlist_loaded()
                # discards the result (request_id != _current_request_id)
                self._abandon_thread()
                self._reset_video_state()
                request_id = str(uuid4())
                self._current_request_id = request_id
                self._loading_url = playlist_url
                self.status_label.setText(tr("dialog.loading_playlist"))
                self._start_playlist_worker(playlist_url, request_id)
                return
            # choice == "single": continues to just one video normal download

        # abandon any pendent request
        # check if that is really the better way to do this
        self._abandon_thread()
        self._reset_video_state()
        
        request_id = str(uuid4())
        self._current_request_id = request_id
        self._loading_url = url

        # classic youtube playlist pipeline
        """ Probably is a good thing that be on a separeted file, like video info service
            or something like that, maybe together to videoInfoWorker class

            Because is that starting and setting a thread - i don't know enough about threading
            right now, but i suspect of that be exists here.
        """
        # only bare playlist links (".../playlist?list=...") - links with a video id
        # (v=) were already handled by _ask_single_or_playlist() above
        if is_youtube_playlist(url) and not self._has_video_id(url):
            self.status_label.setText(tr("dialog.loading_playlist"))
            self._start_playlist_worker(url, request_id)
            return

        # delete previous thumbnail (if any) before requesting a new one,
        # otherwise every pasted URL leaves an orphaned .jpg behind
        self._delete_current_thumb()

        # unique video runtime
        temp_thumb = os.path.join(get_temp_dir(), f"{request_id}.jpg")
        self._current_thumb_path = temp_thumb

        self.status_label.setText(tr("dialog.loading"))

        self._thread = QThread()
        self._worker = VideoInfoWorker(url, temp_thumb, request_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_video_loaded)
        self._worker.error.connect(self._on_video_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        keep_thread(self._thread, self._worker)
        self._thread.start()

    """ Again, i supose that should be on another file, maybe playlist service, 
        maybe together to playlistWorker class, because that use threads for playlist 
        things.
    """
    # playlist worker threads iniciator
    def _start_playlist_worker(self, url, request_id):
        thread = QThread()
        worker = PlaylistLoadWorker(url, request_id)
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker

        thread.started.connect(worker.run)
        # direct slots (no lambda): correct QueuedConnection between the
        # worker thread and the main (UI) thread
        worker.finished.connect(self._on_playlist_loaded)
        worker.error.connect(self._on_playlist_error)
        # quit THIS thread - self._thread may already be another request's
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)

        keep_thread(thread, worker)
        thread.start()

    # clean UI video information
    def _reset_video_state(self):
        self.video_info = None
        self._destroy_trimmer()
        # the preview belongs to the previous link
        self._cancel_preview()
        self.advanced_check.hide()
        self._update_mode_visibility()


    """ =========================
        HANDLERS - MAIN THREAD
      ========================= """

    # set UI components when load a new video information
    @Slot(object, object, str)
    def _on_video_loaded(self, info, thumb_path, request_id):
        if request_id != self._current_request_id:
            return

        self.video_info = info

        if thumb_path:
            self.thumbnail.set_thumbnail(thumb_path)

        title = info.get("title", "")
        if title:
            # suggest a valid name to save
            self.filename_input.setText(safe_filename(title))

        self._populate_quality_selector()

        """ The advanced mode (trimmer) is restricted to single youtube videos
            (playlists go through PlaylistDialog, which has no trimmer), and the
            media duration must be known (the cut bar needs it).
            The preview is loaded later (see _start_preview_worker) and, if it fails,
            the trimmer still works with thumbnail + cut bar.
            Turned off for now, see TRIMMER_ENABLED.
        """
        can_trim = (
            TRIMMER_ENABLED
            and is_youtube(self._loading_url or "")
            and bool(info.get("duration"))
        )
        if can_trim:
            self.advanced_check.show()
            if self.advanced_check.isChecked():
                self._build_trimmer()
        else:
            self.advanced_check.setChecked(False)
            self.advanced_check.hide()
            self._destroy_trimmer()
        self._update_mode_visibility()

        self.status_label.setText(tr("dialog.info_loaded"))

    # UI feedback when was an error getting video informations
    @Slot(str, str)
    def _on_video_error(self, msg, request_id):
        if request_id != self._current_request_id:
            return
        self.status_label.setText(tr("dialog.error", error=msg))


    """ ===========================
        PLAYLIST HANDLERS

        Agina, i supose that should be on a playlist things dedicated file
    ============================= """
    # UI feedback to load playlist process
    @Slot(object, str)
    def _on_playlist_loaded(self, playlist, request_id):
        if request_id != self._current_request_id:
            return

        if not playlist or not playlist.get("entries"):
            self.status_label.setText(tr("dialog.playlist_empty"))
            return

        self.status_label.setText(tr("dialog.playlist_loaded", count=len(playlist["entries"])))

        from ui.playlist_dialog import PlaylistDialog
        dlg = PlaylistDialog(playlist, self)
        if dlg.exec():
            self._results = dlg.get_result()
            self.accept()

    @Slot(str, str)
    def _on_playlist_error(self, msg, request_id):
        if request_id != self._current_request_id:
            return
        self.status_label.setText(tr("dialog.playlist_error", error=msg))


    """ ==========================
        TRIMMER TOOL UI SETTINGS
      ========================== """

    # add trimm tool to UI
    def _build_trimmer(self):
        if not self.video_info:
            return

        # clean older trimmer if were one
        self._destroy_trimmer()

        # late import to isolate dependencies from QtMultimedia
        from ui.components.clip_trimmer import ClipTrimmer

        duration = self.video_info.get("duration")
        self.trimmer = ClipTrimmer(duration, self._current_thumb_path)
        self.trimmer_container.addWidget(self.trimmer)

        # preview already downloaded for this link: reuse it
        if self._preview_path and self._preview_url == self._loading_url:
            self.trimmer.load_preview(self._preview_path)
        # not downloading yet: start (if it's downloading, it loads when finished)
        elif self._preview_worker is None:
            self._start_preview_worker()

        self._update_mode_visibility()

    # download the trimmer preview on background (same thread pattern of the other workers)
    def _start_preview_worker(self):
        request_id = str(uuid4())
        self._preview_request_id = request_id
        self._preview_url = self._loading_url

        thread = QThread()
        worker = PreviewLoadWorker(self._loading_url, get_temp_dir(),
                                   f"preview_{request_id}", request_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_preview_loaded)
        worker.finished.connect(thread.quit)

        self._preview_worker = worker
        # the worker object must live until the thread ends
        keep_thread(thread, worker)
        thread.start()

    # preview download finished (path is None if it failed)
    @Slot(object, str)
    def _on_preview_loaded(self, path, request_id):
        # old request (other link / dialog closing): just remove the file
        if request_id != self._preview_request_id:
            _remove_later(path, 0)
            return
        self._preview_worker = None
        self._preview_path = path
        if self.trimmer:
            self.trimmer.load_preview(path)

    # stop the preview download (if running) and remove the preview file
    def _cancel_preview(self):
        self._preview_request_id = None
        if self._preview_worker is not None:
            try:
                self._preview_worker.cancel()
            except Exception:
                pass
            self._preview_worker = None
        if self._preview_path:
            _remove_later(self._preview_path)
        self._preview_path = None
        self._preview_url = None

    # delete and clean trimm tool from UI
    def _destroy_trimmer(self):
        if self.trimmer:
            try:
                self.trimmer.stop()
            except Exception:
                pass
            self.trimmer_container.removeWidget(self.trimmer)
            self.trimmer.deleteLater()
            self.trimmer = None


    """ ================================
        VIDEO QUALITY - WITH FILE SIZE
      ================================ """
    # file size to friendly text (sizes are estimates, so "~")
    @staticmethod
    def _format_size(size_bytes):
        if not size_bytes:
            return tr("dialog.unknown_size")
        size_mb = size_bytes / (1024 * 1024)
        if size_mb >= 1024:
            return f"~{size_mb/1024:.1f} GB"
        return f"~{size_mb:.1f} MB"

    """ Insert quality informations to quality UI selector.
        MP4: one line per resolution with the real download size (video + audio,
        see VideoInfo._format_response). Resolutions without H.264 on the site
        get a "conversion needed" tag (the file is converted after the download).
        MP3: one disabled line with the estimated size (always 192 kbps).
        Each item data: {"quality_id", "filesize", "label", "needs_conversion"}
    """
    def _populate_quality_selector(self):
        if not self.video_info:
            return

        self.quality_selector.clear()
        self._conversion_warning_shown = False

        # MP3: nothing to choose, just show the space needed
        if self.format_selector.currentText().upper() == "MP3":
            duration = self.video_info.get("duration") or 0
            filesize = int(duration * 192000 / 8) if duration else None
            label = "MP3 192 kbps"
            self.quality_selector.addItem(
                f"{label} ({self._format_size(filesize)})",
                {"quality_id": None, "filesize": filesize, "label": label, "needs_conversion": False},
            )
            self.quality_selector.setEnabled(False)
            return

        formats = sorted(self.video_info.get("formats", []),
                         key=lambda f: f.get("height") or 0, reverse=True)

        default_index = None
        for f in formats:
            height = f.get("height")
            short_label = f"{height}p"
            label = f"{short_label} ({self._format_size(f.get('filesize'))})"
            # h264 False = conversion needed / None = unknown codec (no tag)
            needs_conversion = f.get("h264") is False
            if needs_conversion:
                label += tr("dialog.needs_conversion_suffix")

            quality_id = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            self.quality_selector.addItem(label, {
                "quality_id": quality_id,
                "filesize": f.get("filesize"),
                # to recalculate the size with another audio language (see _confirm)
                "video_filesize": f.get("video_filesize"),
                "has_audio": f.get("has_audio", False),
                "label": short_label,
                "needs_conversion": needs_conversion,
            })

            # default = the highest quality that doesn't need conversion,
            # otherwise every 4K video would be slow without user choice
            if default_index is None and not needs_conversion:
                default_index = self.quality_selector.count() - 1

        self.quality_selector.setEnabled(len(formats) > 0)
        if not formats:
            self.quality_selector.addItem(tr("dialog.no_formats"), None)
            return
        self.quality_selector.setCurrentIndex(default_index if default_index is not None else 0)

    # user chose a quality on selector
    def _on_quality_activated(self, index):
        data = self.quality_selector.itemData(index)
        if isinstance(data, dict) and data.get("needs_conversion"):
            self._show_conversion_warning()

    """ Explain that this quality takes more time: the site doesn't offer it
        on H.264 (the format video editors accept), so it will be converted
        on the user computer after the download.
        Same pattern of the other warnings (checkbox "don't show again").
    """
    def _show_conversion_warning(self):
        self._conversion_warning_shown = True
        if self.settings.get_skip_conversion_warning():
            return

        box = QMessageBox(self)
        box.setWindowTitle(tr("dialog.conversion_title"))
        box.setIcon(QMessageBox.Information)
        box.setText(tr("dialog.conversion_text"))
        dont_show = QCheckBox(tr("common.dont_show_again"))
        box.setCheckBox(dont_show)
        box.addButton(tr("common.close"), QMessageBox.AcceptRole)
        box.exec()

        if dont_show.isChecked():
            self.settings.set_skip_conversion_warning(True)


    """ =====================
        UI ACTIONS FUNCTIONS
      ===================== """
    # choose folder logic
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("common.choose_folder"))
        if folder:
            self.path_input.setText(folder)

    # confirm download setting to start download instantly
    def _confirm(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()

        # validate url and path data
        if not url or not path:
            QMessageBox.warning(self, tr("common.error"), tr("dialog.invalid_url_or_folder"))
            return

        # validate video settings data
        if not self.video_info:
            QMessageBox.warning(self, tr("common.error"), tr("dialog.load_info_first"))
            return

        fmt = self.format_selector.currentText()
        filename = self.filename_input.text().strip()

        # validate saved file name
        if filename and not is_valid_filename(filename):
            bad = invalid_filename_chars(filename)
            QMessageBox.warning(
                self, tr("dialog.invalid_name_title"),
                tr("dialog.invalid_name_text", chars="   ".join(bad))
            )
            return

        selected_quality_id = None
        selected_filesize = None
        # short quality label for the history card (without the size text)
        quality_label = self.quality_selector.currentText()
        data = self.quality_selector.currentData()
        if isinstance(data, dict):
            selected_quality_id = data.get("quality_id") if fmt.upper() == "MP4" else None
            selected_filesize = data.get("filesize")
            quality_label = data.get("label") or quality_label
            # quality selected by default that needs conversion (all of them need):
            # the user must know before the download starts
            if data.get("needs_conversion") and not self._conversion_warning_shown:
                self._show_conversion_warning()

        # advanced mode
        clip_start, clip_end = (None, None)
        if self.advanced_check.isChecked() and self.trimmer:
            clip_start, clip_end = self.trimmer.get_clip()
            # start and end markers at same point = empty clip
            if clip_start is not None and clip_end is not None and clip_end - clip_start < 1:
                QMessageBox.warning(self, tr("dialog.invalid_clip_title"),
                                    tr("dialog.invalid_clip_text"))
                return

        # more than one audio track (dubbed video): the user picks one language
        audio_language = None
        if needs_audio_choice(self.video_info):
            audio_language = self._ask_audio_language()
            if audio_language is None:
                # cancelled: back to the download dialog
                return
            if fmt.upper() == "MP4" and isinstance(data, dict):
                selected_filesize = self._size_with_audio(data, audio_language, selected_filesize)

        original_title = self.video_info.get("title") or tr("common.untitled")
        final_title = filename if filename else safe_filename(original_title)

        """ verify existent equal file on destination folder (offers 3 options)
            - replace existent file;
            - automaticaly rename, addindg numeration like: file_name(1).mp4, file_name(2).mp4, etc;
            - go back and manualy rename.
        """
        overwrite = False
        if file_conflict(path, final_title, fmt):
            existing = expected_output_path(path, final_title, fmt)
            box = QMessageBox(self)
            box.setWindowTitle(tr("dialog.file_exists_title"))
            box.setIcon(QMessageBox.Warning)
            box.setText(tr("dialog.file_exists_text", path=existing))
            overwrite_btn = box.addButton(tr("dialog.replace_file"), QMessageBox.AcceptRole)
            rename_btn = box.addButton(tr("dialog.rename_automatically"), QMessageBox.AcceptRole)
            back_btn = box.addButton(tr("dialog.go_back_rename"), QMessageBox.RejectRole)
            box.setDefaultButton(back_btn)
            box.exec()

            clicked = box.clickedButton()
            if clicked == overwrite_btn:
                overwrite = True
            elif clicked == rename_btn:
                final_title = resolve_unique_title(path, final_title, fmt)
            else:
                # just came back to download dialog and users can rename manualy
                return

        # instantiate final download item with selected data
        self.download_item = DownloadItem(
            url=url,
            title=final_title,
            original_title=original_title,
            format_type=fmt,
            quality=quality_label,
            quality_id=selected_quality_id,
            thumbnail=self._current_thumb_path,
            status="pending",
            output_path=path,
            filesize=selected_filesize,
            clip_start=clip_start,
            clip_end=clip_end,
            overwrite=overwrite,
            audio_language=audio_language,
        )
        self._results = [self.download_item]
        self.accept()

    """ Audio language dialog (see ui/audio_language_dialog.py).
        Returns the chosen yt-dlp language code, or None if cancelled.
    """
    def _ask_audio_language(self):
        dialog = AudioLanguageDialog(self.video_info.get("audio_tracks") or [], self)
        if not dialog.exec():
            return None
        return dialog.selected_language()

    # MP4 size with the chosen audio language instead of the original one
    # (the quality selector shows the size with the original track)
    def _size_with_audio(self, quality_data, language, default):
        if quality_data.get("has_audio"):
            return default
        video_size = quality_data.get("video_filesize")
        audio_size = (self.video_info.get("audio_sizes") or {}).get(language)
        if video_size is None or audio_size is None:
            return default
        return video_size + audio_size

    # items to download list - just 1 for unique content, N to youtube playlists
    def get_results(self):
        return self._results

    # basicaly same thing of get_results - mantained just to avoid broke some old code
    # should be replaced and deleted someday
    def get_result(self):
        return self._results[0] if self._results else None


    """ ====================
        CLEANIG OPERATIONS
      ==================== """
    # left open threads runnig - i supose that is terrible way to do this
    # i will check better options before translate the documentation comments
    def _abandon_thread(self):
        """
        Desvincula a thread de carregamento atual sem bloquear a UI.
        A thread continua viva (registrada por keep_thread) até terminar
        sozinha; seu resultado tardio é ignorado pelo request_id.
        """
        # invalida qualquer resultado em andamento
        self._current_request_id = None
        for attr in ("_thread", "_worker"):
            setattr(self, attr, None)

    # delete the current temp thumbnail file, if any
    def _delete_current_thumb(self):
        path = self._current_thumb_path
        self._current_thumb_path = None
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # run when closes trimmer tool
    # maybe that could be at a trimmer file
    def done(self, result):
        """ Terminate preview player in a non-bloking manner.
            loading threads end up alone on background, we don't use wait() at main thread.
        """
        self._destroy_trimmer()
        self._current_request_id = None
        # stop preview download (if running) and remove the preview file
        self._cancel_preview()
        """ Clean up the thumbnail only if the dialog is being cancelled/closed
            without a confirmed download (result == Accepted keeps the file,
            since DownloadItem.thumbnail still points to it for the history card)
        """
        if result != QDialog.Accepted:
            self._delete_current_thumb()
        super().done(result)