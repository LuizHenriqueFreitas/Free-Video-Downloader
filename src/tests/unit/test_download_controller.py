import pytest
from unittest.mock import MagicMock

from src.controllers.download_controller import DownloadController


# ==========================
# MOCK ITEM
# ==========================

class FakeItem:
    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at


# ==========================
# FIXTURE COM INJEÇÃO DE DEPENDÊNCIA
# ==========================

@pytest.fixture
def controller():
    mock_store = MagicMock()
    mock_store.load.return_value = []

    controller = DownloadController(store=mock_store)

    return controller


# ==========================
# TEST: inicialização carrega dados
# ==========================

def test_init_carrega_dados():
    mock_store = MagicMock()

    fake_items = [
        FakeItem("1", 10),
        FakeItem("2", 20),
    ]

    mock_store.load.return_value = fake_items

    controller = DownloadController(store=mock_store)

    assert controller.items == fake_items
    mock_store.load.assert_called_once()


# ==========================
# TEST: get_history ordena corretamente
# ==========================

def test_get_history_ordena(controller):
    controller.items = [
        FakeItem("1", 10),
        FakeItem("2", 30),
        FakeItem("3", 20),
    ]

    result = controller.get_history()

    ids = [item.id for item in result]

    assert ids == ["2", "3", "1"]


# ==========================
# TEST: add_item adiciona e salva
# ==========================

def test_add_item_adiciona_e_salva(controller):
    item = FakeItem("1", 10)

    controller.add_item(item)

    assert controller.items[0] == item
    controller.store.save.assert_called_once_with(controller.items)


# ==========================
# TEST: add_item insere no topo
# ==========================

def test_add_item_insere_no_topo(controller):
    item1 = FakeItem("1", 10)
    item2 = FakeItem("2", 20)

    controller.items = [item1]

    controller.add_item(item2)

    assert controller.items[0] == item2
    assert controller.items[1] == item1


# ==========================
# TEST: update_item substitui corretamente
# ==========================

def test_update_item_substitui(controller):
    item1 = FakeItem("1", 10)
    controller.items = [item1]

    updated_item = FakeItem("1", 99)

    controller.update_item(updated_item)

    assert controller.items[0].created_at == 99

    controller.store.save.assert_called_once_with(controller.items)


# ==========================
# TEST: update_item não quebra se não achar
# ==========================

def test_update_item_item_nao_encontrado(controller):
    item1 = FakeItem("1", 10)
    controller.items = [item1]

    updated_item = FakeItem("999", 50)

    controller.update_item(updated_item)

    # lista não muda
    assert controller.items[0] == item1

    controller.store.save.assert_not_called()


# ==========================
# TEST: múltiplos updates
# ==========================

def test_update_item_multiplos(controller):
    items = [
        FakeItem("1", 10),
        FakeItem("2", 20),
        FakeItem("3", 30),
    ]

    controller.items = items

    updated = FakeItem("2", 999)

    controller.update_item(updated)

    result = [i.created_at for i in controller.items]

    assert result == [10, 999, 30]


# ==========================
# TEST: save é chamado corretamente
# ==========================

def test_save_chama_store(controller):
    item = FakeItem("1", 10)

    controller.add_item(item)

    controller.store.save.assert_called_once_with(controller.items)