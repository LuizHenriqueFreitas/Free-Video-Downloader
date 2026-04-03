# core/utils.py

import sys
import os

#functions to import file resources 
def get_ytdlp_path():
    """
    Retorna caminho absoluto do yt-dlp.exe
    """
    return resource_path("bin/yt-dlp.exe")

def get_ffmpeg_path():
    """
    Retorna o diretório onde está o ffmpeg
    Funciona tanto em desenvolvimento quanto no executável
    """
    if getattr(sys, "frozen", False):
        # Dentro do EXE
        return resource_path("tools/ffmpeg/bin/")
    else:
        # Em desenvolvimento
        return resource_path("tools/ffmpeg/bin/")

def get_node_path():
    path = resource_path("bin/node/node.exe")
    if not os.path.exists(path):
        raise Exception("Node não encontrado no projeto")
    return path

def get_cookies_path():
    return resource_path("data/cookies.txt")

#path tracker
def resource_path(relative_path):
    """
    Retorna caminho correto tanto em dev quanto em exe (PyInstaller)
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

#cookies existence verify
def cookies_exists():
    return os.path.exists(get_cookies_path())