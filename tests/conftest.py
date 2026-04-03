# tests/conftest.py

import pytest
from datetime import datetime
from models.download_item import DownloadItem


@pytest.fixture
def sample_item():
    item = DownloadItem(
        url="http://test.com",
        title="Test Video",
        format_type="MP4",
        quality="720p",
        thumbnail="thumb.jpg",
        status="pending"
    )
    item.id = "1"
    item.created_at = datetime.now().isoformat()
    return item


@pytest.fixture
def multiple_items():
    items = []
    for i in range(5):
        item = DownloadItem(
            url=f"url_{i}",
            title=f"title_{i}",
            format_type="MP4",
            quality="720p",
            thumbnail="thumb.jpg",
            status="pending"
        )
        item.id = str(i)
        item.created_at = datetime.now().isoformat()
        items.append(item)
    return items