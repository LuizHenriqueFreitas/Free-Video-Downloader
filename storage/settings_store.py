import json
import os

from core.utils import get_user_data_dir


DEFAULTS = {
    "history_count": 20,            # 10, 20 ou 50
    "advanced_mode": False,         # modo simples (False) vs. avançado/corte (True)
    "skip_remove_confirm": False,   # pular o aviso ao remover do histórico
    "skip_playlist_warning": False, # pular o aviso ao baixar playlist
}

ALLOWED_HISTORY_COUNTS = (10, 20, 50)


class SettingsStore:
    """Persistência simples de preferências do usuário em data/settings.json."""

    def __init__(self, file_path=None):
        self.file_path = file_path or os.path.join(get_user_data_dir(), "settings.json")
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._data.update({k: data[k] for k in DEFAULTS if k in data})
        except Exception:
            # arquivo corrompido -> mantém defaults
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print("Erro ao salvar settings:", e)

    # ==========================
    # MÉTODOS AUXILIARES PARA BOOLEANOS
    # ==========================
    def _get_bool(self, key: str, default: bool) -> bool:
        """Retorna valor booleano da configuração"""
        value = self._data.get(key, default)
        return bool(value)

    def _set_bool(self, key: str, value: bool):
        """Salva valor booleano na configuração"""
        self._data[key] = bool(value)
        self._save()

    # ==========================
    # HISTÓRICO
    # ==========================
    def get_history_count(self) -> int:
        value = self._data.get("history_count", DEFAULTS["history_count"])
        if value not in ALLOWED_HISTORY_COUNTS:
            return DEFAULTS["history_count"]
        return value

    def set_history_count(self, value: int):
        if value in ALLOWED_HISTORY_COUNTS:
            self._data["history_count"] = value
            self._save()

    # ==========================
    # MODO DO DIÁLOGO
    # ==========================
    def get_advanced_mode(self) -> bool:
        return bool(self._data.get("advanced_mode", DEFAULTS["advanced_mode"]))

    def set_advanced_mode(self, value: bool):
        self._data["advanced_mode"] = bool(value)
        self._save()

    # ==========================
    # PLAYLIST WARNING
    # ==========================
    def get_skip_playlist_warning(self) -> bool:
        return self._get_bool("skip_playlist_warning", DEFAULTS["skip_playlist_warning"])

    def set_skip_playlist_warning(self, value: bool):
        self._set_bool("skip_playlist_warning", value)

    # ==========================
    # CONFIRMAÇÃO DE REMOÇÃO
    # ==========================
    def get_skip_remove_confirm(self) -> bool:
        return bool(self._data.get("skip_remove_confirm", DEFAULTS["skip_remove_confirm"]))

    def set_skip_remove_confirm(self, value: bool):
        self._data["skip_remove_confirm"] = bool(value)
        self._save()