# tests/unit/test_audio_language_dialog.py

""" Tests for ui/audio_language_dialog.py and DownloadItem.audio_language. """

from core import i18n
from models.download_item import DownloadItem
from ui.audio_language_dialog import AudioLanguageDialog, needs_audio_choice

TRACKS = [
    {"language": "en-US", "original": True, "note": "English (US) original (default), medium"},
    {"language": "pt", "original": False, "note": "Portuguese, medium"},
    {"language": "de", "original": False, "note": "German, medium"},
]


def _labels(dialog):
    return [b.text() for b in dialog._buttons]


class TestNeedsAudioChoice:

    def test_many_tracks(self):
        assert needs_audio_choice({"audio_tracks": TRACKS}) is True

    def test_single_or_no_track(self):
        assert needs_audio_choice({"audio_tracks": TRACKS[:1]}) is False
        assert needs_audio_choice({}) is False
        assert needs_audio_choice(None) is False


class TestAudioLanguageDialog:

    def test_original_first_and_preselected(self):
        dialog = AudioLanguageDialog(TRACKS)
        assert _labels(dialog)[0] == "Inglês (EUA) (original)"
        assert dialog.selected_language() == "en-US"

    def test_others_sorted_in_app_language(self):
        i18n.set_language("pt_BR")
        assert _labels(AudioLanguageDialog(TRACKS))[1:] == ["Alemão", "Português"]
        i18n.set_language("en")
        assert _labels(AudioLanguageDialog(TRACKS))[1:] == ["German", "Portuguese"]

    def test_only_one_can_be_chosen(self):
        dialog = AudioLanguageDialog(TRACKS)
        buttons = list(dialog._buttons)
        buttons[2].setChecked(True)
        assert sum(b.isChecked() for b in buttons) == 1
        assert dialog.selected_language() == dialog._buttons[buttons[2]]


class TestDownloadItemAudioLanguage:

    def test_round_trip(self):
        item = DownloadItem(url="u", title="t", audio_language="pt")
        assert DownloadItem.from_dict(item.to_dict()).audio_language == "pt"

    def test_old_history_without_field(self):
        data = DownloadItem(url="u", title="t").to_dict()
        del data["audio_language"]
        assert DownloadItem.from_dict(data).audio_language is None


class TestSortIgnoresAccents:

    def test_accented_name_sorted_with_its_letter(self):
        i18n.set_language("pt_BR")
        tracks = [
            {"language": "en", "original": True, "note": ""},
            {"language": "vi", "original": False, "note": ""},   # Vietnamita
            {"language": "ar", "original": False, "note": ""},   # Árabe
            {"language": "de", "original": False, "note": ""},   # Alemão
        ]
        assert _labels(AudioLanguageDialog(tracks))[1:] == ["Alemão", "Árabe", "Vietnamita"]
