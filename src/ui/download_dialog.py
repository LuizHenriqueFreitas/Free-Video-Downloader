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

from core.video_info import VideoInfo, PreviewDownloader
from core.utils import (
    resource_path, cookies_exists, looks_like_url,
    is_youtube_playlist,
    file_conflict, resolve_unique_title, expected_output_path,
    safe_filename, invalid_filename_chars, is_valid_filename, get_temp_dir
)
from ui.components.thumbnail_widget import ThumbnailWidget
from models.download_item import DownloadItem
from storage.settings_store import SettingsStore

# load placeholder video image
PLACEHOLDER = resource_path("assets/placeholder.png")

""" Mantain all alive threads refence untill their end, without block the UI.
    that avoid freezing (thread.wait() on main thread) and crash "QThread
    destroyed while runnig" if dialog were closed.
"""
_LIVE_THREADS = set()

# add new to live_threads set
def _keep_thread(thread):
    _LIVE_THREADS.add(thread)
    thread.finished.connect(lambda: _LIVE_THREADS.discard(thread))


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

        self.setWindowTitle("Novo Download")
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
        layout.addWidget(QLabel("URL do vídeo (YouTube, TikTok, Instagram, etc.):"))
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self._on_url_changed)
        layout.addWidget(self.url_input)

        # advanced mode (trimmer) - hide untill get video data
        self.advanced_check = QCheckBox("Selecionar trecho do vídeo (modo avançado)")
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
        # that will need to be translated at location update
        format_layout.addWidget(QLabel("Formato:"))
        self.format_selector = QComboBox()
        # that will need to be translated at location update
        self.format_selector.addItems(["MP4", "MP3"])
        self.format_selector.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_selector)

        # that will need to be translated at location update
        format_layout.addWidget(QLabel("Qualidade:"))
        self.quality_selector = QComboBox()
        self.quality_selector.setEnabled(False)
        # "activated" is emitted only by user action (mouse/keyboard), not when
        # the list is filled by code - so the warning never pops up by itself
        self.quality_selector.activated.connect(self._on_quality_activated)
        format_layout.addWidget(self.quality_selector)
        layout.addLayout(format_layout)

        # select final file folder
        # that will need to be translated at location update
        layout.addWidget(QLabel("Pasta de destino:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        # that will need to be translated at location update
        path_button = QPushButton("Escolher pasta")
        path_button.clicked.connect(self._choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)

        # fila saved name - default is the original media title
        # that will need to be translated at location update
        layout.addWidget(QLabel("Nome do arquivo (opcional):"))
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
        # that will need to be translated at location update
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        # that will need to be translated at location update
        self.ok_button = QPushButton("Adicionar")
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
            # that will need to be translated at location update
            self.status_label.setText("Carregando informações...")
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
            self.filename_warning.setText(
                # that will need to be translated at location update
                "O nome do arquivo não pode conter: " + "  ".join(bad)
            )
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
        # that will need to be translated at location update
        msg.setWindowTitle("Playlist detectada")
        msg.setIcon(QMessageBox.Question)
        # that will need to be translated at location update
        msg.setText(
            "🔗 **Playlist detectada!**\n\n"
            "A URL informada pertence a uma playlist do YouTube.\n\n"
            "O que você deseja baixar?"
        )

        # that will need to be translated at location update
        btn_video = msg.addButton("📹 Apenas este vídeo", QMessageBox.AcceptRole)
        btn_playlist = msg.addButton("📋 Toda a playlist", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancelar", QMessageBox.RejectRole) # why is that off?
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
            # that will need to be translated at location update
            self.status_label.setText("⚠ Cookies não configurados")
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
                # that will need to be translated at location update
                self.url_input.clear()
                self.status_label.setText("Cancelado pelo usuário")
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
                # that will need to be translated at location update
                self.status_label.setText("Carregando playlist...")
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
            # that will need to be translated at location update
            self.status_label.setText("Carregando playlist...")
            self._start_playlist_worker(url, request_id)
            return

        # delete previous thumbnail (if any) before requesting a new one,
        # otherwise every pasted URL leaves an orphaned .jpg behind
        self._delete_current_thumb()

        # unique video runtime
        temp_thumb = os.path.join(get_temp_dir(), f"{request_id}.jpg")
        self._current_thumb_path = temp_thumb

        # that will need to be translated at location update
        self.status_label.setText("Carregando...")

        self._thread = QThread()
        self._worker = VideoInfoWorker(url, temp_thumb, request_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_video_loaded)
        self._worker.error.connect(self._on_video_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        _keep_thread(self._thread)
        self._thread.start()

    """ Again, i supose that should be on another file, maybe playlist service, 
        maybe together to playlistWorker class, because that use threads for playlist 
        things.
    """
    # playlist worker threads iniciator
    def _start_playlist_worker(self, url, request_id):
        self._thread = QThread()
        self._worker = PlaylistLoadWorker(url, request_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        """ I will check this logic before translate that documentation commentaries
        """
        # Conexão direta ao slot (sem lambda): garante QueuedConnection correto
        # entre a thread do worker e a thread principal (UI).
        self._worker.finished.connect(self._on_playlist_loaded)
        self._worker.error.connect(self._on_playlist_error)
        self._worker.finished.connect(lambda *_: self._thread.quit())
        self._worker.error.connect(lambda *_: self._thread.quit())
        self._thread.finished.connect(self._thread.deleteLater)

        _keep_thread(self._thread)
        self._thread.start()

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

        """ The advanced mode (trimmer) is available to any site yt-dlp can download,
            as long as the media duration is known (the cut bar needs it).
            The preview is loaded later (see _start_preview_worker) and, if it fails,
            the trimmer still works with thumbnail + cut bar.
        """
        can_trim = bool(info.get("duration"))
        if can_trim:
            self.advanced_check.show()
            if self.advanced_check.isChecked():
                self._build_trimmer()
        else:
            self.advanced_check.setChecked(False)
            self.advanced_check.hide()
            self._destroy_trimmer()
        self._update_mode_visibility()

        # that will need to be translated at location update
        self.status_label.setText("✔ Informações carregadas")

    # UI feedback when was an error getting video informations
    @Slot(str, str)
    def _on_video_error(self, msg, request_id):
        if request_id != self._current_request_id:
            return
        self.status_label.setText(f"Erro: {msg}")


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
            # that will need to be translated at location update
            self.status_label.setText("Nenhum vídeo encontrado na playlist.")
            return

        # that will need to be translated at location update
        self.status_label.setText(
            f"✔ Playlist carregada: {len(playlist['entries'])} vídeos"
        )

        from ui.playlist_dialog import PlaylistDialog
        dlg = PlaylistDialog(playlist, self)
        if dlg.exec():
            self._results = dlg.get_result()
            self.accept()

    @Slot(str, str)
    def _on_playlist_error(self, msg, request_id):
        if request_id != self._current_request_id:
            return
        # that will need to be translated at location update
        self.status_label.setText(f"Erro ao carregar playlist: {msg}")


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

        # that will need to be translated at location update
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
        worker.finished.connect(lambda *_: thread.quit())
        thread.finished.connect(thread.deleteLater)
        # the worker object must live until the thread ends
        thread.finished.connect(worker.deleteLater)

        self._preview_worker = worker
        _keep_thread(thread)
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
    # that will need to be translated at location update
    @staticmethod
    def _format_size(size_bytes):
        if not size_bytes:
            return "tamanho desconhecido"
        size_mb = size_bytes / (1024 * 1024)
        if size_mb >= 1024:
            return f"~{size_mb/1024:.1f} GB"
        return f"~{size_mb:.1f} MB"

    """ Insert quality informations to quality UI selector.
        MP4: one line per resolution with the real download size (video + audio,
        see VideoInfo._format_response). Resolutions without H.264 on the site
        get "necessário conversão" (the file is converted after the download).
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
                # that will need to be translated at location update
                label += " — necessário conversão"

            quality_id = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            self.quality_selector.addItem(label, {
                "quality_id": quality_id,
                "filesize": f.get("filesize"),
                "label": short_label,
                "needs_conversion": needs_conversion,
            })

            # default = the highest quality that doesn't need conversion,
            # otherwise every 4K video would be slow without user choice
            if default_index is None and not needs_conversion:
                default_index = self.quality_selector.count() - 1

        self.quality_selector.setEnabled(len(formats) > 0)
        if not formats:
            # that will need to be translated at location update
            self.quality_selector.addItem("Nenhum formato disponível", None)
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
        # that will need to be translated at location update
        box.setWindowTitle("Esta qualidade precisa de conversão")
        box.setIcon(QMessageBox.Information)
        # that will need to be translated at location update
        box.setText(
            "O site não oferece essa resolução no formato aceito pelos editores "
            "de vídeo (Premiere, Vegas, CapCut e outros).\n\n"
            "Depois do download, o Get Media Free vai converter o vídeo no seu "
            "computador para que ele possa ser usado na edição. Isso pode levar "
            "bastante tempo, às vezes mais do que a duração do próprio vídeo, "
            "dependendo do seu computador.\n\n"
            "O progresso e o tempo restante aparecem no card do download."
        )
        # that will need to be translated at location update
        dont_show = QCheckBox("Não mostrar esta mensagem novamente")
        box.setCheckBox(dont_show)
        # that will need to be translated at location update
        box.addButton("Fechar", QMessageBox.AcceptRole)
        box.exec()

        if dont_show.isChecked():
            self.settings.set_skip_conversion_warning(True)


    """ =====================
        UI ACTIONS FUNCTIONS
      ===================== """
    # choose folder logic
    def _choose_folder(self):
        # that will need to be translated at location update
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

    # confirm download setting to start download instantly
    def _confirm(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()

        # validate url and path data
        if not url or not path:
            # that will need to be translated at location update
            QMessageBox.warning(self, "Erro", "URL ou pasta inválida")
            return

        # validate video settings data
        if not self.video_info:
            # that will need to be translated at location update
            QMessageBox.warning(self, "Erro", "Carregue as informações do vídeo primeiro")
            return

        fmt = self.format_selector.currentText()
        filename = self.filename_input.text().strip()

        # validate saved file name
        if filename and not is_valid_filename(filename):
            bad = invalid_filename_chars(filename)
            # that will need to be translated at location update
            QMessageBox.warning(
                self, "Nome inválido",
                "O nome do arquivo não pode conter os caracteres:\n\n"
                + "   ".join(bad)
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
                # that will need to be translated at location update
                QMessageBox.warning(self, "Trecho inválido",
                                    "O trecho selecionado precisa ter pelo menos 1 segundo.")
                return

        # that will need to be translated at location update
        original_title = self.video_info.get("title", "Sem título")
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
            # that will need to be translated at location update
            box.setWindowTitle("Arquivo já existe")
            box.setIcon(QMessageBox.Warning)
            # that will need to be translated at location update
            box.setText(
                f"Já existe um arquivo com este nome e tipo:\n\n{existing}\n\n"
                f"O que deseja fazer?"
            )
            # that will need to be translated at location update
            overwrite_btn = box.addButton("Substituir arquivo", QMessageBox.AcceptRole)
            rename_btn = box.addButton("Renomear automaticamente", QMessageBox.AcceptRole)
            back_btn = box.addButton("Voltar e trocar o nome", QMessageBox.RejectRole)
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
        )
        self._results = [self.download_item]
        self.accept()

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
        A thread continua viva (registrada em _LIVE_THREADS) até terminar
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