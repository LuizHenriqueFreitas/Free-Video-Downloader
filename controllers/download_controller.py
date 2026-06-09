#controller/downloader_controller
from storage.history_store import HistoryStore


class DownloadController:
    def __init__(self, store=None):
        self.store = store or HistoryStore()
        self.items = self.store.load()

    def get_history(self):
        return sorted(self.items, key=lambda x: x.created_at, reverse=True)

    def add_item(self, item):
        self.items.insert(0, item)
        self._save()

    def update_item(self, item):
        found = False

        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[i] = item
                found = True
                break
        if found:
            self._save()

    def remove_item(self, item):
        item_id = getattr(item, "id", item)
        before = len(self.items)
        self.items = [x for x in self.items if x.id != item_id]
        if len(self.items) != before:
            self._save()

    def _save(self):
        self.store.save(self.items)