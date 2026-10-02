# ui/audio_language_dialog.py

""" Here you will find:
    - AudioLanguageDialog: asks which audio language to download when a video
      has more than one audio track (dubbed youtube videos);
    - languages shown in the app language, the original track first and
      preselected; only one can be chosen (radio buttons).

    Single videos only: playlists always download the original track.
"""

import unicodedata

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QScrollArea, QWidget,
)

from core.i18n import tr, audio_language_name


# sort key ignoring accents and case: "Árabe" goes with the "A"s
def _sort_key(name):
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


# True when there is something to choose
def needs_audio_choice(video_info):
    return len((video_info or {}).get("audio_tracks") or []) > 1


class AudioLanguageDialog(QDialog):
    # tracks: VideoInfo "audio_tracks" - [{"language", "original", "note"}, ...]
    def __init__(self, tracks, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("audio.title"))
        self.setMinimumWidth(380)
        self._buttons = {}

        layout = QVBoxLayout(self)
        text = QLabel(tr("audio.text", count=len(tracks)))
        text.setWordWrap(True)
        layout.addWidget(text)

        # original first, then alphabetical in the app language
        entries = []
        for track in tracks:
            name = audio_language_name(track["language"], track.get("note", ""))
            if track.get("original"):
                name = tr("audio.original", name=name)
            entries.append((not track.get("original"), _sort_key(name), name, track["language"]))
        entries.sort()

        # dubbed videos can have 20+ languages: scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        options = QVBoxLayout(content)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for _, _, name, language in entries:
            button = QRadioButton(name)
            self._group.addButton(button)
            self._buttons[button] = language
            options.addWidget(button)
        options.addStretch()
        scroll.setWidget(content)
        scroll.setMinimumHeight(min(360, 34 * len(entries) + 10))
        layout.addWidget(scroll)

        # original (the 1st one) preselected
        first = next(iter(self._buttons), None)
        if first is not None:
            first.setChecked(True)

        buttons = QHBoxLayout()
        cancel = QPushButton(tr("common.cancel"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("audio.confirm"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    # chosen yt-dlp language code
    def selected_language(self):
        button = self._group.checkedButton()
        return self._buttons.get(button)
