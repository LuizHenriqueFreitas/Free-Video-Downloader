# ui/components/clip_trimmer.py

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from src.ui.components.range_slider import RangeSlider


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


class ClipTrimmer(QWidget):
    """
    Seleção de trecho (início/fim) com preview de vídeo.
    Tenta usar o player real (QMediaPlayer); se o stream não tocar,
    cai automaticamente para thumbnail + barra de tempo.
    """

    def __init__(self, duration, thumbnail_path=None, parent=None):
        super().__init__(parent)
        self._duration = int(duration or 0)
        self._thumbnail_path = thumbnail_path
        self._player = None
        self._audio = None
        self._fallback = False
        self._seeking = False   # usuário arrastando a barra de reprodução

        self._setup_ui()

        if self._duration <= 0:
            # sem duração conhecida não dá para cortar com precisão
            self._enter_fallback("Duração desconhecida — corte indisponível.")
            self.slider.setEnabled(False)

    # ==========================
    # UI
    # ==========================
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ---- Área de vídeo / thumbnail ----
        self.video_widget = QVideoWidget()
        self.video_widget.setFixedHeight(220)
        self.video_widget.setStyleSheet("background-color: #000;")
        layout.addWidget(self.video_widget)

        self.fallback_label = QLabel()
        self.fallback_label.setFixedHeight(220)
        self.fallback_label.setAlignment(Qt.AlignCenter)
        self.fallback_label.setStyleSheet("background-color: #000; color: #aaa;")
        self.fallback_label.hide()
        layout.addWidget(self.fallback_label)

        # ---- Controles de reprodução ----
        controls = QHBoxLayout()
        self.play_btn = QPushButton("▶ Reproduzir")
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)

        self.current_label = QLabel(f"00:00 / {format_time(self._duration)}")
        self.current_label.setStyleSheet("color: #ccc;")
        controls.addWidget(self.current_label)
        controls.addStretch()

        self.preview_clip_btn = QPushButton("Pré-visualizar trecho")
        self.preview_clip_btn.clicked.connect(self._preview_clip)
        controls.addWidget(self.preview_clip_btn)
        layout.addLayout(controls)

        # ---- Barra de REPRODUÇÃO (assistir/avançar o vídeo) — estilo YouTube ----
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

        # ---- Barra de SELEÇÃO DE TRECHO (início/fim do download) ----
        trim_caption = QLabel("Trecho a baixar (arraste os marcadores):")
        trim_caption.setStyleSheet("color: #4CAF50; font-size: 11px;")
        layout.addWidget(trim_caption)

        self.slider = RangeSlider()
        self.slider.setMaximum(max(1, self._duration))
        self.slider.rangeChanged.connect(self._on_range_changed)
        self.slider.sliderPressed.connect(self._pause)
        layout.addWidget(self.slider)

        # ---- Marcadores ----
        marks = QHBoxLayout()
        self.mark_start_btn = QPushButton("Início = agora")
        self.mark_start_btn.clicked.connect(self._mark_start)
        self.mark_end_btn = QPushButton("Fim = agora")
        self.mark_end_btn.clicked.connect(self._mark_end)

        self.start_label = QLabel("Início: 00:00")
        self.end_label = QLabel(f"Fim: {format_time(self._duration)}")
        self.start_label.setStyleSheet("color: #4CAF50;")
        self.end_label.setStyleSheet("color: #4CAF50;")

        marks.addWidget(self.mark_start_btn)
        marks.addWidget(self.start_label)
        marks.addStretch()
        marks.addWidget(self.end_label)
        marks.addWidget(self.mark_end_btn)
        layout.addLayout(marks)

        self.hint_label = QLabel("Arraste os marcadores ou use os botões para definir o trecho.")
        self.hint_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.hint_label)

    # ==========================
    # PREVIEW (carregar URL)
    # ==========================
    def load_preview(self, url):
        if self._fallback:
            return
        if not url:
            self._enter_fallback("Preview indisponível — use a barra de tempo.")
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

            self._player.setSource(QUrl(url))
        except Exception as e:
            self._enter_fallback(f"Preview indisponível ({e}).")

    # ==========================
    # FALLBACK
    # ==========================
    def _enter_fallback(self, message=""):
        self._fallback = True
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
        self.video_widget.hide()
        self.play_btn.setEnabled(False)
        self.preview_clip_btn.setEnabled(False)
        self.mark_start_btn.setEnabled(False)
        self.mark_end_btn.setEnabled(False)
        self.seek_slider.setEnabled(False)   # sem player, não há o que avançar

        # mostra thumbnail como referência
        if self._thumbnail_path and os.path.exists(self._thumbnail_path):
            pix = QPixmap(self._thumbnail_path)
            if not pix.isNull():
                self.fallback_label.setPixmap(
                    pix.scaled(self.fallback_label.size(),
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        if not self.fallback_label.pixmap() or self.fallback_label.pixmap().isNull():
            self.fallback_label.setText(message or "Preview indisponível")
        self.fallback_label.show()

        if message:
            self.hint_label.setText(message + " A seleção do trecho continua funcionando.")

    def _on_player_error(self, error, error_string=""):
        if error != QMediaPlayer.NoError:
            self._enter_fallback("Não foi possível reproduzir o vídeo aqui.")

    def _on_media_status(self, status):
        if status == QMediaPlayer.InvalidMedia:
            self._enter_fallback("Formato de stream não suportado para preview.")

    # ==========================
    # PLAYER EVENTS
    # ==========================
    def _on_duration_changed(self, duration_ms):
        # se o yt-dlp não informou duração, usa a do player
        if self._duration <= 0 and duration_ms > 0:
            self._duration = duration_ms // 1000
            self.slider.setEnabled(True)
            self.slider.setMaximum(max(1, self._duration))
            self.seek_slider.setRange(0, max(1, self._duration))
            self.end_label.setText(f"Fim: {format_time(self._duration)}")

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

    # ==========================
    # BARRA DE REPRODUÇÃO (SEEK)
    # ==========================
    def _on_seek_pressed(self):
        self._seeking = True

    def _on_seek_moved(self, value):
        # mostra o tempo enquanto arrasta e move o playhead da barra de trecho
        self.current_label.setText(f"{format_time(value)} / {format_time(self._duration)}")
        self.slider.setPlayhead(value)
        if self._player:
            self._player.setPosition(value * 1000)

    def _on_seek_released(self):
        if self._player:
            self._player.setPosition(self.seek_slider.value() * 1000)
        self._seeking = False

    # ==========================
    # AÇÕES
    # ==========================
    def _toggle_play(self):
        if not self._player:
            return
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self.play_btn.setText("▶ Reproduzir")
        else:
            self._player.play()
            self.play_btn.setText("⏸ Pausar")

    def _pause(self):
        if self._player and self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self.play_btn.setText("▶ Reproduzir")

    def _preview_clip(self):
        if not self._player:
            return
        self._player.setPosition(self.slider.start() * 1000)
        self._preview_stop_at = self.slider.end()
        self._player.play()
        self.play_btn.setText("⏸ Pausar")

    def _current_seconds(self):
        if self._player:
            return self._player.position() // 1000
        return 0

    def _mark_start(self):
        self.slider.setStart(self._current_seconds())

    def _mark_end(self):
        self.slider.setEnd(self._current_seconds())

    def _on_range_changed(self, start, end):
        self.start_label.setText(f"Início: {format_time(start)}")
        self.end_label.setText(f"Fim: {format_time(end)}")

    # ==========================
    # RESULTADO
    # ==========================
    def is_full_range(self):
        """True se o trecho cobre o vídeo inteiro (sem corte real)."""
        return self.slider.start() <= 0 and self.slider.end() >= self._duration

    def get_clip(self):
        """Retorna (start, end) em segundos, ou (None, None) se for o vídeo inteiro."""
        if self._duration <= 0 or self.is_full_range():
            return (None, None)
        return (self.slider.start(), self.slider.end())

    def stop(self):
        # Encerramento LIMPO do player. É preciso liberar a mídia com
        # setSource(QUrl()) para que o backend FFmpeg pare as threads de rede e
        # decodificação; caso contrário aparece "QThread: Destroyed while thread
        # is still running" (e "Failed to send close message" do TLS) ao destruir
        # o player com uma conexão de streaming ainda aberta.
        p = self._player
        a = self._audio
        self._player = None
        self._audio = None
        if p is not None:
            try:
                p.disconnect()      # evita callbacks durante o teardown
            except Exception:
                pass
            try:
                p.stop()
            except Exception:
                pass
            try:
                p.setVideoOutput(None)
                p.setAudioOutput(None)
            except Exception:
                pass
            try:
                p.setSource(QUrl())  # libera a mídia -> encerra as threads internas
            except Exception:
                pass
            p.deleteLater()
        if a is not None:
            a.deleteLater()

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)
