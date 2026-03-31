#controller/downloader_controller

from storage.history_store import HistoryStore


class DownloadController:
    def __init__(self):
        self.store = HistoryStore()
        self.items = self.store.load()

    def get_history(self):
        return sorted(self.items, key=lambda x: x.created_at, reverse=True)

    def add_item(self, item):
        self.items.insert(0, item)
        self._save()

    def update_item(self, item):
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[i] = item
                break
        self._save()

    def _save(self):
        self.store.save(self.items)