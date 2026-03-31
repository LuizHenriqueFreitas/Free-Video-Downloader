#storage/history_store

import json
import os
from models.download_item import DownloadItem

FILE_PATH = "data/history.json"


class HistoryStore:
    def __init__(self):
        os.makedirs("data", exist_ok=True)

    def load(self):
        if not os.path.exists(FILE_PATH):
            return []

        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [DownloadItem.from_dict(x) for x in data]
        except:
            return []

    def save(self, items):
        # ordena e limita
        items = sorted(items, key=lambda x: x.created_at, reverse=True)
        items = items[:20]

        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump([x.to_dict() for x in items], f, indent=2)