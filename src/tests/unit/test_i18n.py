# tests/unit/test_i18n.py

""" Tests for core/i18n.py and the locales/ catalogs. """

import string
import sys

import pytest

from core import i18n
from core.i18n import tr
from locales import en, pt_BR
from storage.settings_store import SettingsStore


def _placeholders(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


# ---------------------------------------------------------------------------
# catalogs
# ---------------------------------------------------------------------------

class TestCatalogs:

    def test_same_keys_on_every_language(self):
        assert set(pt_BR.STRINGS) == set(en.STRINGS)

    @pytest.mark.parametrize("key", sorted(pt_BR.STRINGS))
    def test_same_placeholders_on_every_language(self, key):
        assert _placeholders(pt_BR.STRINGS[key]) == _placeholders(en.STRINGS[key])

    def test_every_language_has_a_display_name(self):
        assert set(i18n.LANGUAGE_NAMES) == set(i18n.SUPPORTED_LANGUAGES)


# ---------------------------------------------------------------------------
# tr()
# ---------------------------------------------------------------------------

class TestTr:

    def test_current_language(self):
        i18n.set_language("en")
        assert tr("common.cancel") == "Cancel"
        i18n.set_language("pt_BR")
        assert tr("common.cancel") == "Cancelar"

    def test_explicit_language(self):
        assert tr("common.cancel", lang="en") == "Cancel"

    def test_placeholders(self):
        assert tr("dialog.playlist_loaded", lang="en", count=3) == "✔ Playlist loaded: 3 videos"

    def test_missing_key_shows_key(self):
        assert tr("does.not_exist") == "does.not_exist"

    def test_missing_on_language_falls_back_to_default(self, monkeypatch):
        monkeypatch.delitem(en.STRINGS, "common.cancel")
        assert tr("common.cancel", lang="en") == "Cancelar"

    def test_missing_placeholder_value_keeps_text(self):
        assert tr("dialog.playlist_loaded", lang="en", other=1) == "✔ Playlist loaded: {count} videos"

    def test_unknown_language_falls_back_to_default(self):
        i18n.set_language("xx")
        assert i18n.get_language() == i18n.DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# language detection
# ---------------------------------------------------------------------------

class TestNormalizeLanguage:

    @pytest.mark.parametrize("value, expected", [
        ("brazilianportuguese", "pt_BR"),   # Inno Setup name
        ("english", "en"),                  # Inno Setup name
        ("pt-BR", "pt_BR"),
        ("pt_BR.UTF-8", "pt_BR"),
        ("Portuguese_Brazil", "pt_BR"),     # Windows locale.getlocale()
        ("en_US", "en"),
        ("English_United States", "en"),
        ("fr_FR", None),
        ("", None),
        (None, None),
    ])
    def test_values(self, value, expected):
        assert i18n.normalize_language(value) == expected


class TestInstallerLanguage:

    def _frozen_exe(self, monkeypatch, folder):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(folder / "GetMediaFree.exe"))

    def test_dev_mode_has_none(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert i18n.get_installer_language() is None

    def test_reads_ini(self, monkeypatch, tmp_path):
        self._frozen_exe(monkeypatch, tmp_path)
        (tmp_path / "language.ini").write_text("[Settings]\nLanguage=english\n", encoding="utf-8")
        assert i18n.get_installer_language() == "en"

    def test_missing_ini(self, monkeypatch, tmp_path):
        self._frozen_exe(monkeypatch, tmp_path)
        assert i18n.get_installer_language() is None

    def test_broken_ini(self, monkeypatch, tmp_path):
        self._frozen_exe(monkeypatch, tmp_path)
        (tmp_path / "language.ini").write_text("not an ini file", encoding="utf-8")
        assert i18n.get_installer_language() is None


class TestResolveLanguage:

    def _store(self, tmp_path):
        return SettingsStore(file_path=str(tmp_path / "settings.json"))

    def _installer(self, monkeypatch, value):
        monkeypatch.setattr(i18n, "get_installer_language", lambda: value)

    def _system(self, monkeypatch, value):
        monkeypatch.setattr(i18n, "get_system_language", lambda: value)

    def test_saved_setting_wins(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        store.set_language("en")
        self._installer(monkeypatch, None)
        self._system(monkeypatch, "pt_BR")
        assert i18n.resolve_language(store) == "en"

    def test_installer_when_nothing_saved(self, monkeypatch, tmp_path):
        self._installer(monkeypatch, "en")
        self._system(monkeypatch, "pt_BR")
        store = self._store(tmp_path)
        assert i18n.resolve_language(store) == "en"
        assert store.get_language() == "en"

    def test_new_installer_choice_replaces_saved(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        store.set_installer_language("pt_BR")
        store.set_language("pt_BR")
        # reinstalled choosing english
        self._installer(monkeypatch, "en")
        assert i18n.resolve_language(store) == "en"

    def test_same_installer_choice_keeps_app_selection(self, monkeypatch, tmp_path):
        store = self._store(tmp_path)
        store.set_installer_language("pt_BR")
        # changed on the app selector after installing
        store.set_language("en")
        self._installer(monkeypatch, "pt_BR")
        assert i18n.resolve_language(store) == "en"

    def test_system_language_without_installer(self, monkeypatch, tmp_path):
        self._installer(monkeypatch, None)
        self._system(monkeypatch, "en")
        assert i18n.resolve_language(self._store(tmp_path)) == "en"

    def test_default_when_nothing_known(self, monkeypatch, tmp_path):
        self._installer(monkeypatch, None)
        self._system(monkeypatch, None)
        assert i18n.resolve_language(self._store(tmp_path)) == i18n.DEFAULT_LANGUAGE
