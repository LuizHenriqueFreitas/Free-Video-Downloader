#storage/history_store

import json
import os
from models.download_item import DownloadItem

class HistoryStore:
    def __init__(self, file_path="data/history.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def load(self):
        if not os.path.exists(self.file_path):
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DownloadItem.from_dict(x) for x in data]
        except:
            return []

    def save(self, items):
        # ordena e limita
        items = sorted(items, key=lambda x: x.created_at, reverse=True)
        items = items[:20]

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([x.to_dict() for x in items], f, indent=2)