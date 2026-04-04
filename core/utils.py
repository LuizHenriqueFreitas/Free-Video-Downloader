# core/utils.py

import sys
import os
import stat

# ==========================
# DIRETÓRIO DE DADOS DO USUÁRIO (persistente)
# ==========================

def get_user_data_dir():
    """
    Retorna o diretório onde os dados do usuário serão armazenados (cookies, history, etc.).
    Em desenvolvimento: ./data
    No executável: pasta 'data' ao lado do .exe
    """
    if getattr(sys, 'frozen', False):
        # Executável: usa o diretório do próprio .exe
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

# ==========================
# RECURSOS INTERNOS (empacotados no .exe)
# ==========================

def resource_path(relative_path):
    """
    Retorna caminho correto para recursos internos (bin, tools, assets)
    que são empacotados dentro do executável (apenas leitura).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_ytdlp_path():
    return resource_path("bin/yt-dlp.exe")

def get_ffmpeg_path():
    # Retorna o diretório (não o arquivo) para o --ffmpeg-location
    return resource_path("tools/ffmpeg/bin/")

def get_node_path():
    path = resource_path("bin/node/node.exe")
    if not os.path.exists(path):
        raise Exception("Node não encontrado no projeto")
    return path

# ==========================
# COOKIES (dados do usuário)
# ==========================

def get_cookies_path():
    """Caminho para o arquivo de cookies (dentro do diretório de dados do usuário)."""
    return os.path.join(get_user_data_dir(), "cookies.txt")

def cookies_exists():
    return os.path.exists(get_cookies_path())

def secure_cookies_file(path: str):
    """Restringe permissões do arquivo (Unix: 600, Windows: readonly)."""
    if not os.path.exists(path):
        return
    try:
        # Unix-like: apenas dono lê/escreve
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except:
        # Windows: tenta tornar somente leitura (opcional)
        try:
            os.chmod(path, stat.S_IREAD)
        except:
            pass

def save_cookies(content: bytes):
    path = get_cookies_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    secure_cookies_file(path)