# models/download_item.py

import uuid, time

class DownloadItem:
    def __init__(self, url, title, original_title=None, format_type="MP4", quality="best", quality_id=None, thumbnail=None, status="pending", output_path=None, file_path=None, filesize=None):
        self.id = str(uuid.uuid4())
        self.url = url
        self.title = title          # nome do arquivo (pode ser personalizado)
        self.original_title = original_title or title  # título original do vídeo
        self.format_type = format_type
        self.quality = quality
        self.quality_id = quality_id
        self.thumbnail = thumbnail
        self.status = status
        self.output_path = output_path
        self.file_path = file_path
        self.created_at = time.time()
        self.filesize = filesize

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "original_title": self.original_title,
            "format_type": self.format_type,
            "quality": self.quality,
            "quality_id": self.quality_id,
            "thumbnail": self.thumbnail,
            "status": self.status,
            "output_path": self.output_path,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "filesize": self.filesize,
        }

    @classmethod
    def from_dict(cls, data):
        item = cls(
            url=data["url"],
            title=data["title"],
            original_title=data.get("original_title", data["title"]),
            format_type=data["format_type"],
            quality=data["quality"],
            quality_id=data.get("quality_id"),
            thumbnail=data.get("thumbnail"),
            status=data["status"],
            output_path=data.get("output_path"),
            file_path=data.get("file_path"),
            filesize=data.get("filesize"),
        )
        item.id = data["id"]
        item.created_at = data.get("created_at", time.time())
        return item