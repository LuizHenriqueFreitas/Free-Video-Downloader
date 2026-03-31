#models/download_item.py

import uuid
from datetime import datetime
import re


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


class DownloadItem:
    def __init__(
        self,
        url,
        title,
        format_type,
        quality,
        thumbnail="",
        status="pending",
        file_path="",
        resolution="",
        output_path="",
    ):
        self.id = str(uuid.uuid4())

        self.url = url
        self.title = sanitize_filename(title or "video")

        self.format_type = format_type
        self.quality = quality

        self.thumbnail = thumbnail
        self.status = status

        self.file_path = file_path
        self.output_path = output_path
        self.resolution = resolution

        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "format_type": self.format_type,
            "quality": self.quality,
            "thumbnail": self.thumbnail,
            "status": self.status,
            "file_path": self.file_path,
            "output_path": self.output_path,
            "resolution": self.resolution,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data):
        item = DownloadItem(
            url=data.get("url"),
            title=data.get("title"),
            format_type=data.get("format_type"),
            quality=data.get("quality"),
            thumbnail=data.get("thumbnail", ""),
            status=data.get("status", "pending"),
            file_path=data.get("file_path", ""),
            resolution=data.get("resolution", ""),
            output_path=data.get("output_path", ""),
        )

        item.id = data.get("id", item.id)
        item.created_at = data.get("created_at", item.created_at)

        return item