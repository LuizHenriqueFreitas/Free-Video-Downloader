# tests/conftest.py

import pytest
from datetime import datetime
from models.download_item import DownloadItem


@pytest.fixture(scope="session", autouse=True)
def _qapplication():
    """
    Garante uma QApplication única para a sessão de testes.
    Necessária para testes que usam QThread/QTimer/sinais do Qt
    (caso o pytest-qt não esteja instalado).
    """
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _default_language():
    """
    As mensagens esperadas pelos testes estão em português: fixa o idioma
    padrão em cada teste, mesmo se algum teste anterior trocou o idioma.
    """
    from core import i18n
    i18n.set_language(i18n.DEFAULT_LANGUAGE)
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


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