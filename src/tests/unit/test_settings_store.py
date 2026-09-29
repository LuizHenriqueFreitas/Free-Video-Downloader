# tests/unit/test_settings_store.py

""" Tests for storage/settings_store.py - conversion warning setting (A03). """

import json

from storage.settings_store import SettingsStore


class TestSkipConversionWarning:

    def test_default_is_false(self, tmp_path):
        store = SettingsStore(file_path=str(tmp_path / "settings.json"))
        assert store.get_skip_conversion_warning() is False

    def test_set_and_persist(self, tmp_path):
        path = tmp_path / "settings.json"
        SettingsStore(file_path=str(path)).set_skip_conversion_warning(True)
        assert SettingsStore(file_path=str(path)).get_skip_conversion_warning() is True
        assert json.loads(path.read_text())["skip_conversion_warning"] is True

    def test_old_settings_file_without_key(self, tmp_path):
        # settings.json from older versions doesn't have the key
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"history_count": 10}))
        store = SettingsStore(file_path=str(path))
        assert store.get_skip_conversion_warning() is False
        assert store.get_history_count() == 10
