# ui/download_dialog.py

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

from core.video_info import VideoInfo, pick_preview_url
from core.utils import (
    resource_path, cookies_exists, looks_like_url, is_youtube,
    is_youtube_playlist,
    file_conflict, resolve_unique_title, expected_output_path,
    safe_filename, invalid_filename_chars, is_valid_filename,
)
from ui.components.thumbnail_widget import ThumbnailWidget
from models.download_item import DownloadItem
from storage.settings_store import SettingsStore


PLACEHOLDER = resource_path("assets/placeholder.png")


# Mantém referências de threads vivas até terminarem, sem bloquear a UI.
# Evita tanto o congelamento (thread.wait() na thread principal) quanto o
# crash "QThread destroyed while running" caso o diálogo feche antes.
_LIVE_THREADS = set()


def _keep_thread(thread):
    _LIVE_THREADS.add(thread)
    thread.finished.connect(lambda: _LIVE_THREADS.discard(thread))


# ==========================
# WORKER: carrega playlist em background
# ==========================
class PlaylistLoadWorker(QObject):
    # Inclui request_id nos sinais para que o slot saiba a qual pedido responder
    # sem precisar de lambdas com captura (que causam problemas de entrega
    # entre threads no PySide6 com QueuedConnection).
    finished = Signal(object, str)   # (playlist_dict, request_id)
    error = Signal(str, str)         # (msg, request_id)

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


# ==========================
# WORKER (THREAD SAFE)
# ==========================
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
                os.makedirs("temp", exist_ok=True)
                r = requests.get(thumb_url, timeout=10)
                thumb_path = self.temp_path
                with open(thumb_path, "wb") as f:
                    f.write(r.content)

            self.finished.emit(info, thumb_path, self.request_id)

        except Exception as e:
            self.error.emit(str(e), self.request_id)


# ==========================
# DIALOG
# ==========================
class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Novo Download")
        self.setMinimumSize(560, 600)

        self.settings = SettingsStore()

        self.video_info = None
        self.download_item = None
        self.trimmer = None
        self._results = []          # itens a baixar (atualmente 1 = vídeo único)

        # controle de requisição
        self._current_request_id = None
        self._thread = None
        self._worker = None
        self._current_thumb_path = None
        self._loading_url = None

        # debounce
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self._load_video_info)

        self._setup_ui()

    # ==========================
    # UI
    # ==========================
    def _setup_ui(self):
        # Conteúdo rolável (garante que os controles do preview fiquem acessíveis
        # mesmo em telas menores); botões Cancelar/Adicionar fixos no rodapé.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        self.main_layout = layout

        # URL
        layout.addWidget(QLabel("URL do vídeo (YouTube, TikTok, Instagram, etc.):"))
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self._on_url_changed)
        layout.addWidget(self.url_input)

        # Modo avançado (corte de trecho) — OCULTO até carregar o vídeo
        self.advanced_check = QCheckBox("Selecionar trecho do vídeo (modo avançado)")
        self.advanced_check.setChecked(self.settings.get_advanced_mode())
        self.advanced_check.toggled.connect(self._on_mode_toggled)
        self.advanced_check.hide()
        layout.addWidget(self.advanced_check)

        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Thumbnail (modo simples)
        self.thumbnail = ThumbnailWidget(PLACEHOLDER)
        layout.addWidget(self.thumbnail)

        # Container do trimmer (modo avançado) — preenchido ao carregar info
        self.trimmer_container = QVBoxLayout()
        layout.addLayout(self.trimmer_container)

        # Formato + Qualidade
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP4", "MP3"])
        self.format_selector.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_selector)

        format_layout.addWidget(QLabel("Qualidade:"))
        self.quality_selector = QComboBox()
        self.quality_selector.setEnabled(False)
        format_layout.addWidget(self.quality_selector)
        layout.addLayout(format_layout)

        # Pasta
        layout.addWidget(QLabel("Pasta de destino:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_button = QPushButton("Escolher pasta")
        path_button.clicked.connect(self._choose_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_button)
        layout.addLayout(path_layout)

        # Nome
        layout.addWidget(QLabel("Nome do arquivo (opcional):"))
        self.filename_input = QLineEdit()
        self.filename_input.textChanged.connect(self._validate_filename_live)
        layout.addWidget(self.filename_input)

        self.filename_warning = QLabel("")
        self.filename_warning.setStyleSheet("color: #F44336; font-size: 11px;")
        self.filename_warning.hide()
        layout.addWidget(self.filename_warning)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Botões (fixos no rodapé, fora da área rolável)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 6, 10, 10)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = QPushButton("Adicionar")
        self.ok_button.clicked.connect(self._confirm)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        outer.addLayout(button_layout)

        self._update_mode_visibility()

    # ==========================
    # EVENTOS
    # ==========================
    def _on_url_changed(self):
        text = self.url_input.text().strip()
        if looks_like_url(text):
            self.status_label.setText("Carregando informações...")
            self.load_timer.start(800)

    def _on_format_changed(self, value):
        if value.upper() == "MP4":
            self.quality_selector.setEnabled(True)
            if self.video_info:
                self._populate_quality_selector()
        else:
            self.quality_selector.clear()
            self.quality_selector.setEnabled(False)

    def _on_mode_toggled(self, checked):
        self.settings.set_advanced_mode(checked)
        self._update_mode_visibility()
        if checked and self.video_info:
            self._build_trimmer()
        elif not checked:
            self._destroy_trimmer()

    def _update_mode_visibility(self):
        advanced = self.advanced_check.isChecked() and self.advanced_check.isVisible()
        # no modo avançado, o preview do trimmer substitui a thumbnail simples
        self.thumbnail.setVisible(not advanced)
        if self.trimmer:
            self.trimmer.setVisible(advanced)

    # ==========================
    # VALIDAÇÃO DO NOME
    # ==========================
    def _validate_filename_live(self):
        name = self.filename_input.text()
        bad = invalid_filename_chars(name)
        if bad:
            self.filename_warning.setText(
                "O nome do arquivo não pode conter: " + "  ".join(bad)
            )
            self.filename_warning.show()
            self.ok_button.setEnabled(False)
        else:
            self.filename_warning.hide()
            self.ok_button.setEnabled(True)

    # ==========================
    # DETECÇÃO DE PLAYLIST EM URL DE VÍDEO
    # ==========================
    def _extract_playlist_id_from_video_url(self, url):
        """Extrai ID da playlist de uma URL de vídeo do YouTube (&list=...)"""
        import re
        match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', url)
        return match.group(1) if match else None

    def _build_playlist_url_from_id(self, playlist_id):
        """Converte ID da playlist em URL completa"""
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    def _ask_single_or_playlist(self, video_url, playlist_url):
        """Pergunta ao usuário se quer baixar só o vídeo ou a playlist inteira"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Playlist detectada")
        msg.setIcon(QMessageBox.Question)
        msg.setText(
            "🔗 **Playlist detectada!**\n\n"
            "A URL informada pertence a uma playlist do YouTube.\n\n"
            "O que você deseja baixar?"
        )
        
        btn_video = msg.addButton("📹 Apenas este vídeo", QMessageBox.AcceptRole)
        btn_playlist = msg.addButton("📋 Toda a playlist", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancelar", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_video)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == btn_video:
            return "single"
        elif clicked == btn_playlist:
            return "playlist"
        else:
            return "cancel"

    def _extract_playlist_id_from_video_url(self, url):
        """Extrai ID da playlist de uma URL de vídeo do YouTube (&list=...)"""
        import re
        match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', url)
        return match.group(1) if match else None

    def _build_playlist_url_from_id(self, playlist_id):
        """Converte ID da playlist em URL completa"""
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    def _ask_single_or_playlist(self, video_url, playlist_url):
        """Pergunta ao usuário se quer baixar só o vídeo ou a playlist inteira"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Playlist detectada")
        msg.setIcon(QMessageBox.Question)
        msg.setText(
            "🔗 **Playlist detectada!**\n\n"
            "A URL informada pertence a uma playlist do YouTube.\n\n"
            "O que você deseja baixar?"
        )
        
        btn_video = msg.addButton("📹 Apenas este vídeo", QMessageBox.AcceptRole)
        btn_playlist = msg.addButton("📋 Toda a playlist", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancelar", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_video)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == btn_video:
            return "single"
        elif clicked == btn_playlist:
            return "playlist"
        else:
            return "cancel"

    # ==========================
    # LOAD (THREAD SAFE)
    # ==========================
    def _load_video_info(self):
        url = self.url_input.text().strip()
        if not url:
            return

        if not cookies_exists():
            self.status_label.setText("⚠ Cookies não configurados")
            return

        # ---- DETECTAR PLAYLIST EM URL DE VÍDEO (&list=) ----
        playlist_id = self._extract_playlist_id_from_video_url(url)
        if playlist_id and not is_youtube_playlist(url):
            playlist_url = self._build_playlist_url_from_id(playlist_id)
            choice = self._ask_single_or_playlist(url, playlist_url)
            
            if choice == "cancel":
                self.status_label.setText("Cancelado pelo usuário")
                return
            elif choice == "playlist":
                # Carrega a playlist inteira
                self._start_playlist_worker(playlist_url, str(uuid4()))
                return
            # choice == "single": continua fluxo normal de vídeo único

        # ---- RESTANTE DO CÓDIGO ORIGINAL ----
        # Abandona qualquer requisição anterior
        self._abandon_thread()
        self._reset_video_state()
        
        request_id = str(uuid4())
        self._current_request_id = request_id
        self._loading_url = url

        # ---- Playlist do YouTube (clássica) ----
        if is_youtube_playlist(url):
            self.status_label.setText("Carregando playlist...")
            self._start_playlist_worker(url, request_id)
            return

        # ---- Vídeo único ----
        temp_thumb = os.path.join("temp", f"{request_id}.jpg")
        self._current_thumb_path = temp_thumb

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

    def _start_playlist_worker(self, url, request_id):
        self._thread = QThread()
        self._worker = PlaylistLoadWorker(url, request_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        # Conexão direta ao slot (sem lambda): garante QueuedConnection correto
        # entre a thread do worker e a thread principal (UI).
        self._worker.finished.connect(self._on_playlist_loaded)
        self._worker.error.connect(self._on_playlist_error)
        self._worker.finished.connect(lambda *_: self._thread.quit())
        self._worker.error.connect(lambda *_: self._thread.quit())
        self._thread.finished.connect(self._thread.deleteLater)

        _keep_thread(self._thread)
        self._thread.start()

    def _reset_video_state(self):
        self.video_info = None
        self._destroy_trimmer()
        self.advanced_check.hide()
        self._update_mode_visibility()

    # ==========================
    # HANDLERS (THREAD PRINCIPAL)
    # ==========================
    @Slot(object, object, str)
    def _on_video_loaded(self, info, thumb_path, request_id):
        if request_id != self._current_request_id:
            return

        self.video_info = info

        if thumb_path:
            self.thumbnail.set_thumbnail(thumb_path)

        title = info.get("title", "")
        if title:
            # sugere um nome já válido (sem caracteres proibidos)
            self.filename_input.setText(safe_filename(title))

        self._populate_quality_selector()

        # O modo avançado (corte por trecho) só é oferecido quando dá para
        # GARANTIR o preview do vídeo. Na prática, isso só funciona no YouTube
        # e quando há um formato progressivo tocável. Caso contrário, escondemos
        # a opção e usamos apenas o modo simples.
        can_preview = is_youtube(self._loading_url) and bool(pick_preview_url(info))
        if can_preview:
            self.advanced_check.show()
            if self.advanced_check.isChecked():
                self._build_trimmer()
        else:
            self.advanced_check.setChecked(False)
            self.advanced_check.hide()
            self._destroy_trimmer()
        self._update_mode_visibility()

        self.status_label.setText("✔ Informações carregadas")

    @Slot(str, str)
    def _on_video_error(self, msg, request_id):
        if request_id != self._current_request_id:
            return
        self.status_label.setText(f"Erro: {msg}")

    # ==========================
    # PLAYLIST HANDLERS
    # ==========================
    @Slot(object, str)
    def _on_playlist_loaded(self, playlist, request_id):
        if request_id != self._current_request_id:
            return

        if not playlist or not playlist.get("entries"):
            self.status_label.setText("Nenhum vídeo encontrado na playlist.")
            return

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
        self.status_label.setText(f"Erro ao carregar playlist: {msg}")

    # ==========================
    # TRIMMER (CORTE)
    # ==========================
    def _build_trimmer(self):
        if not self.video_info:
            return

        self._destroy_trimmer()

        # import tardio para isolar dependência de QtMultimedia
        from ui.components.clip_trimmer import ClipTrimmer

        duration = self.video_info.get("duration")
        self.trimmer = ClipTrimmer(duration, self._current_thumb_path)
        self.trimmer_container.addWidget(self.trimmer)

        preview_url = pick_preview_url(self.video_info)
        self.trimmer.load_preview(preview_url)

        self._update_mode_visibility()

    def _destroy_trimmer(self):
        if self.trimmer:
            try:
                self.trimmer.stop()
            except Exception:
                pass
            self.trimmer_container.removeWidget(self.trimmer)
            self.trimmer.deleteLater()
            self.trimmer = None

    # ==========================
    # QUALIDADE (com tamanho)
    # ==========================
    def _populate_quality_selector(self):
        if not self.video_info:
            return

        formats = self.video_info.get("formats", [])
        video_formats = [
            f for f in formats
            if f.get("height") and f.get("vcodec") != "none"
        ]

        unique_heights = {}
        for f in video_formats:
            height = f.get("height")
            if height not in unique_heights:
                unique_heights[height] = f
            else:
                if f.get("tbr", 0) > unique_heights[height].get("tbr", 0):
                    unique_heights[height] = f

        sorted_heights = sorted(unique_heights.keys(), reverse=True)

        self.quality_selector.clear()
        for height in sorted_heights:
            f = unique_heights[height]
            label = f"{height}p"
            filesize = f.get("filesize") or f.get("filesize_approx")
            if filesize:
                size_mb = filesize / (1024 * 1024)
                if size_mb >= 1024:
                    label += f" ({size_mb/1024:.1f} GB)"
                else:
                    label += f" ({size_mb:.1f} MB)"
            else:
                label += " (tamanho desconhecido)"

            quality_id = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            self.quality_selector.addItem(label, (quality_id, filesize))

        self.quality_selector.setEnabled(len(sorted_heights) > 0)
        if not sorted_heights:
            self.quality_selector.addItem("Nenhum formato disponível", (None, None))

    # ==========================
    # AÇÕES
    # ==========================
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if folder:
            self.path_input.setText(folder)

    def _confirm(self):
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()

        if not url or not path:
            QMessageBox.warning(self, "Erro", "URL ou pasta inválida")
            return

        if not self.video_info:
            QMessageBox.warning(self, "Erro", "Carregue as informações do vídeo primeiro")
            return

        fmt = self.format_selector.currentText()
        filename = self.filename_input.text().strip()

        # valida nome do arquivo (caracteres proibidos)
        if filename and not is_valid_filename(filename):
            bad = invalid_filename_chars(filename)
            QMessageBox.warning(
                self, "Nome inválido",
                "O nome do arquivo não pode conter os caracteres:\n\n"
                + "   ".join(bad)
            )
            return

        selected_quality_id = None
        selected_filesize = None
        if fmt.upper() == "MP4":
            data = self.quality_selector.currentData()
            if data and isinstance(data, tuple):
                selected_quality_id, selected_filesize = data

        # Trecho (modo avançado)
        clip_start, clip_end = (None, None)
        if self.advanced_check.isChecked() and self.trimmer:
            clip_start, clip_end = self.trimmer.get_clip()

        original_title = self.video_info.get("title", "Sem título")
        final_title = filename if filename else safe_filename(original_title)

        # ---- Verificação de arquivo existente (3 opções) ----
        overwrite = False
        if file_conflict(path, final_title, fmt):
            existing = expected_output_path(path, final_title, fmt)
            box = QMessageBox(self)
            box.setWindowTitle("Arquivo já existe")
            box.setIcon(QMessageBox.Warning)
            box.setText(
                f"Já existe um arquivo com este nome e tipo:\n\n{existing}\n\n"
                f"O que deseja fazer?"
            )
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
                # "Voltar": fecha só o aviso e mantém o diálogo aberto para editar
                return

        self.download_item = DownloadItem(
            url=url,
            title=final_title,
            original_title=original_title,
            format_type=fmt,
            quality=self.quality_selector.currentText(),
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

    def get_results(self):
        """Lista de itens a baixar (1 para vídeo único, N para playlist)."""
        return self._results

    def get_result(self):
        """Compatibilidade: primeiro item (ou None)."""
        return self._results[0] if self._results else None

    # ==========================
    # LIMPEZA
    # ==========================
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

    def done(self, result):
        # encerra o player do preview de forma não-bloqueante; as threads de
        # carregamento terminam sozinhas (não usamos wait() na thread principal).
        self._destroy_trimmer()
        self._current_request_id = None
        super().done(result)