# ui/components/clip_trimmer.py

""" Here you will find:
    - Trimmer tool component settings;
    - UI implementation;
    - media player logic (local preview file) + thumbnail fallback;
    - "loading" state while the preview is downloaded;
    - player buttons logic (play, pause, etc);
    - markers and timelines logic and UI implementation;
"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QUrl, QTimer, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.i18n import tr
from ui.components.range_slider import RangeSlider

# numerical time operations to friendly visual feedback
def format_time(seconds):
    if seconds is None:
        seconds = 0
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

""" Clip select (start/end), with video preview.
    Starts on "loading" state (thumbnail + cut bar already working) while the
    preview file is downloaded (see PreviewDownloader at core/video_info.py).
    Then try to use real player (QMediaPlayer), if ocurred an error
    automaticaly change just to thumbnail + timebar and selectors.
"""
# main class from this file
class ClipTrimmer(QWidget):
    def __init__(self, duration, thumbnail_path=None, parent=None):
        super().__init__(parent)
        self._duration = int(duration or 0)
        self._thumbnail_path = thumbnail_path
        self._player = None
        self._audio = None
        self._fallback = False
        self._seeking = False

        self._setup_ui()

        # check if the clip start is earlier than end 
        if self._duration <= 0:
            self._enter_fallback(tr("trimmer.unknown_duration"))
            self.slider.setEnabled(False)
        else:
            self._show_loading()


    """ ====================
        UI IMPLEMENTATION 
      =================== """
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ===== Video Area / Thumbnail =======
        self.video_widget = QVideoWidget()
        self.video_widget.setFixedHeight(220)
        self.video_widget.setStyleSheet("background-color: #000;")
        layout.addWidget(self.video_widget)

        # activate when is not possible load real time media player
        self.fallback_label = QLabel()
        self.fallback_label.setFixedHeight(220)
        self.fallback_label.setAlignment(Qt.AlignCenter)
        self.fallback_label.setStyleSheet("background-color: #000; color: #aaa;")
        self.fallback_label.hide()
        layout.addWidget(self.fallback_label)

        # ===== Player Controlls ======
        controls = QHBoxLayout()
        self.play_btn = QPushButton(tr("trimmer.play"))
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)

        self.current_label = QLabel(f"00:00 / {format_time(self._duration)}")
        self.current_label.setStyleSheet("color: #ccc;")
        controls.addWidget(self.current_label)
        controls.addStretch()

        self.preview_clip_btn = QPushButton(tr("trimmer.preview_clip"))
        self.preview_clip_btn.clicked.connect(self._preview_clip)
        controls.addWidget(self.preview_clip_btn)
        layout.addLayout(controls)

        # ==== Media Player Bar Feedback (click to travel video timeline) ======
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, max(1, self._duration))
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 5px; background: #555; border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #e53935; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff; width: 13px; height: 13px;
                margin: -4px 0; border-radius: 7px;
            }
            QSlider::handle:horizontal:hover { background: #f0f0f0; }
        """)
        layout.addWidget(self.seek_slider)

        # ===== Clip Selection Bar - marks clip start and end =====
        trim_caption = QLabel(tr("trimmer.caption"))
        trim_caption.setStyleSheet("color: #4CAF50; font-size: 11px;")
        layout.addWidget(trim_caption)

        self.slider = RangeSlider()
        self.slider.setMaximum(max(1, self._duration))
        self.slider.rangeChanged.connect(self._on_range_changed)
        self.slider.sliderPressed.connect(self._pause)
        layout.addWidget(self.slider)

        # ===== Markers =======
        marks = QHBoxLayout()
        self.mark_start_btn = QPushButton(tr("trimmer.mark_start"))
        self.mark_start_btn.clicked.connect(self._mark_start)
        self.mark_end_btn = QPushButton(tr("trimmer.mark_end"))
        self.mark_end_btn.clicked.connect(self._mark_end)

        self.start_label = QLabel(tr("trimmer.start", time=format_time(0)))
        self.end_label = QLabel(tr("trimmer.end", time=format_time(self._duration)))
        self.start_label.setStyleSheet("color: #4CAF50;")
        self.end_label.setStyleSheet("color: #4CAF50;")

        marks.addWidget(self.mark_start_btn)
        marks.addWidget(self.start_label)
        marks.addStretch()
        marks.addWidget(self.end_label)
        marks.addWidget(self.mark_end_btn)
        layout.addLayout(marks)

        self.hint_label = QLabel(tr("trimmer.hint"))
        self.hint_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.hint_label)


    """ ========================
          LOAD PREVIEW FILE
      ======================== """
    # "loading" state: thumbnail + message, cut bar works, player controls wait
    def _show_loading(self):
        self.video_widget.hide()
        self._set_player_controls_enabled(False)
        self._show_thumbnail(tr("trimmer.loading_preview"))
        self.hint_label.setText(tr("trimmer.loading_preview_hint"))

    # load the local preview file (None = preview download failed)
    def load_preview(self, path):
        if self._fallback:
            return
        if not path or not os.path.exists(path):
            self._enter_fallback(tr("trimmer.preview_unavailable_link"))
            return

        try:
            self._player = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
            self._player.setVideoOutput(self.video_widget)

            self._player.errorOccurred.connect(self._on_player_error)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)
            self._player.mediaStatusChanged.connect(self._on_media_status)

            # leave "loading" state
            self.fallback_label.hide()
            self.video_widget.show()
            self._set_player_controls_enabled(True)
            self.hint_label.setText(tr("trimmer.hint"))

            # local file: fromLocalFile() is needed (Windows paths like C:\...)
            self._player.setSource(QUrl.fromLocalFile(path))
        except Exception as e:
            self._enter_fallback(tr("trimmer.preview_unavailable_error", error=e))

    # enable/disable everything that depends on the player
    def _set_player_controls_enabled(self, enabled):
        self.play_btn.setEnabled(enabled)
        self.preview_clip_btn.setEnabled(enabled)
        self.mark_start_btn.setEnabled(enabled)
        self.mark_end_btn.setEnabled(enabled)
        self.seek_slider.setEnabled(enabled)

    # show media thumbnail as visual reference (or the message if there's none)
    def _show_thumbnail(self, message):
        self.fallback_label.clear()
        if self._thumbnail_path and os.path.exists(self._thumbnail_path):
            pix = QPixmap(self._thumbnail_path)
            if not pix.isNull():
                self.fallback_label.setPixmap(
                    pix.scaled(self.fallback_label.width() or 390, self.fallback_label.height(),
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        if not self.fallback_label.pixmap() or self.fallback_label.pixmap().isNull():
            self.fallback_label.setText(message or tr("trimmer.preview_unavailable"))
        self.fallback_label.show()


    """ ====================
            FALLBACK
      =================== """
    # set widget fallback state
    def _enter_fallback(self, message=""):
        self._fallback = True
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
        self.video_widget.hide()
        self._set_player_controls_enabled(False)

        # show media thumbnail as visual reference
        self._show_thumbnail(message)

        if message:
            self.hint_label.setText(tr("trimmer.fallback_hint", message=message))

    # player generic error alert
    def _on_player_error(self, error, error_string=""):
        if error != QMediaPlayer.NoError:
            self._enter_fallback(tr("trimmer.cant_play"))

    # media preview error alert
    def _on_media_status(self, status):
        if status == QMediaPlayer.InvalidMedia:
            self._enter_fallback(tr("trimmer.unsupported_stream"))


    """ ===================
          PLAYER EVENTS
      =================== """
    # run when clip duration changes
    def _on_duration_changed(self, duration_ms):
        # get player timestamp settings in addition to yt-dlp data
        if self._duration <= 0 and duration_ms > 0:
            self._duration = duration_ms // 1000
            self.slider.setEnabled(True)
            self.slider.setMaximum(max(1, self._duration))
            self.seek_slider.setRange(0, max(1, self._duration))
            self.end_label.setText(tr("trimmer.end", time=format_time(self._duration)))

    # run when markers position changes
    def _on_position_changed(self, pos_ms):
        secs = pos_ms // 1000
        self.current_label.setText(f"{format_time(secs)} / {format_time(self._duration)}")
        self.slider.setPlayhead(secs)
        if not self._seeking:
            self.seek_slider.setValue(secs)
        # para a pré-visualização do trecho ao chegar no fim
        if getattr(self, "_preview_stop_at", None) is not None and secs >= self._preview_stop_at:
            self._pause()
            self._preview_stop_at = None


    """ ========================
        REPRODUCTION BAR - SEEK
      ======================= """

    # change widget state
    def _on_seek_pressed(self):
        self._seeking = True

    # show media time while scrolling the playhed at navegation bar
    def _on_seek_moved(self, value):
        self.current_label.setText(f"{format_time(value)} / {format_time(self._duration)}")
        self.slider.setPlayhead(value)
        if self._player:
            self._player.setPosition(value * 1000)

    # run when user finish seek nagevation and return to widget normal state
    def _on_seek_released(self):
        if self._player:
            self._player.setPosition(self.seek_slider.value() * 1000)
        self._seeking = False


    """ =================
            ACTIONS
      ================ """
    # play button logic
    def _toggle_play(self):
        if not self._player:
            return
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self.play_btn.setText(tr("trimmer.play"))
        else:
            self._player.play()
            self.play_btn.setText(tr("trimmer.pause"))

    # pause button logic
    def _pause(self):
        if self._player and self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self.play_btn.setText(tr("trimmer.play"))

    # preview clip UI information logic
    def _preview_clip(self):
        if not self._player:
            return
        self._player.setPosition(self.slider.start() * 1000)
        self._preview_stop_at = self.slider.end()
        self._player.play()
        self.play_btn.setText(tr("trimmer.pause"))

    # timeline counter logic - used by markers to correct visual position on screen
    def _current_seconds(self):
        if self._player:
            return self._player.position() // 1000
        return 0

    # clip start marker logic
    def _mark_start(self):
        self.slider.setStart(self._current_seconds())

    # clip end marker logic
    def _mark_end(self):
        self.slider.setEnd(self._current_seconds())

    # update start/end text feedback when clip range changes
    def _on_range_changed(self, start, end):
        self.start_label.setText(tr("trimmer.start", time=format_time(start)))
        self.end_label.setText(tr("trimmer.end", time=format_time(end)))


    """ ===============
            RESULT
      ============== """
    # true is the clip cover all the original video duration - without real cut
    def is_full_range(self):
        return self.slider.start() <= 0 and self.slider.end() >= self._duration

    # return (start, end) in seconds, or "None" if was the original start/end
    def get_clip(self):
        if self._duration <= 0 or self.is_full_range():
            return (None, None)
        return (self.slider.start(), self.slider.end())

    def stop(self):
        """ Clean player ending. Is necessary release media with seSource(QUrl())
            to the FFmpeg stop the network and decodification threads.
            Or "Qthread: Destroyed while thread is still runnig" and probably
            "Failed to send close message" errors will happend when destroy
            the player with a streaming connection open yet

            player.stop()/setSource(QUrl()) can block for a few seconds on an
            active network stream (Qt Multimedia FFmpeg backend on Linux), which
            would freeze the whole dialog since this runs on the GUI thread when
            the dialog is being closed. So the actual teardown is deferred to the
            next event loop iteration, and the player/audio are detached from
            this widget's parenting first so they survive this widget's deleteLater().

            disconnect() is deferred too, and runs only after stop(): calling it
            synchronously while media is actively playing can make the GUI thread
            block/deadlock contending with the FFmpeg backend's decoder thread for
            the signal-connection lock. Once stop() has halted playback there is
            no more contention, so disconnect() becomes cheap and safe there.
            Any signal that fires in the meantime is harmless: self._player is
            already None below, and every slot guards on it before touching the
            player.
        """
        p = self._player
        a = self._audio
        self._player = None
        self._audio = None
        if p is None:
            return

        try:
            p.setParent(None)
        except Exception:
            pass
        if a is not None:
            try:
                a.setParent(None)
            except Exception:
                pass

        def _teardown():
            try:
                p.stop()
            except Exception:
                pass
            try:
                # avoid callback while the rest of teardown runs.
                # bare p.disconnect() raises TypeError on this PySide6 binding
                # ("not enough arguments") - has to be called as QObject.disconnect(p)
                QObject.disconnect(p)
            except Exception:
                pass
            try:
                p.setVideoOutput(None)
                p.setAudioOutput(None)
            except Exception:
                pass
            try:
                p.setSource(QUrl())
            except Exception:
                pass
            try:
                p.deleteLater()
            except Exception:
                pass
            if a is not None:
                try:
                    a.deleteLater()
                except Exception:
                    pass

        QTimer.singleShot(0, _teardown)

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)
