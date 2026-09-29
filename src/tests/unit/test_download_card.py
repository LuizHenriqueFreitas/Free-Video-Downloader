# tests/unit/test_download_card.py

""" Tests for ui/components/download_card.py - conversion progress (A03). """

from ui.components.download_card import format_remaining, DownloadCard
from models.download_item import DownloadItem


class TestFormatRemaining:

    def test_calculating(self):
        assert format_remaining(None) == "calculando tempo…"
        assert format_remaining(-1) == "calculando tempo…"

    def test_seconds(self):
        assert format_remaining(45) == "~45 s restantes"

    def test_minutes(self):
        assert format_remaining(720) == "~12 min restantes"

    def test_hours(self):
        assert format_remaining(3900) == "~1 h 05 min restantes"


class TestConversionBar:

    def _card(self):
        item = DownloadItem(url="https://x", title="video", status="downloading", output_path="/tmp")
        return DownloadCard(item)

    def test_conversion_mode_text_and_color(self):
        card = self._card()
        card.update_conversion("convert", 42, 180)
        assert card.progress_bar.value() == 42
        assert card.progress_bar.format() == "Convertendo para H.264… 42%% • ~3 min restantes"
        assert "#2196F3" in card.progress_bar.styleSheet()

    def test_cut_text(self):
        card = self._card()
        card.update_conversion("cut", 60, 40)
        assert card.progress_bar.format().startswith("Cortando trecho…")

    def test_unknown_duration_busy_bar(self):
        card = self._card()
        card.update_conversion("convert", -1, -1)
        assert card.progress_bar.maximum() == 0

    def test_download_progress_ignored_during_conversion(self):
        card = self._card()
        card.update_conversion("convert", 10, -1)
        card.update_progress(100)
        assert card.progress_bar.value() == 10

    def test_status_change_resets_to_download_bar(self):
        card = self._card()
        card.update_conversion("convert", 10, -1)
        card.update_status("error")
        card.update_status("downloading")
        assert "#4CAF50" in card.progress_bar.styleSheet()
        card.update_progress(5)
        assert card.progress_bar.value() == 5
