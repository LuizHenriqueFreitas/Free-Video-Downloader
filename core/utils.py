# core/utils.py

import sys
import os
import re
import stat


# ==========================
# PLATAFORMA / URL
# ==========================

# domínios -> nome amigável da plataforma
_PLATFORM_DOMAINS = {
    "youtube": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "tiktok": ("tiktok.com",),
    "instagram": ("instagram.com", "instagr.am"),
    "facebook": ("facebook.com", "fb.watch", "fb.com"),
    "twitter": ("twitter.com", "x.com"),
    "vimeo": ("vimeo.com",),
    "twitch": ("twitch.tv",),
}


def detect_platform(url: str) -> str:
    """Identifica a plataforma a partir da URL. Retorna 'generic' se desconhecida."""
    if not url:
        return "generic"
    u = url.lower()
    for platform, domains in _PLATFORM_DOMAINS.items():
        if any(d in u for d in domains):
            return platform
    return "generic"


def looks_like_url(text: str) -> bool:
    """Heurística simples: parece um link http(s)?"""
    if not text:
        return False
    return bool(re.search(r"https?://[^\s]+", text.strip()))


def is_youtube(url: str) -> bool:
    return detect_platform(url) == "youtube"


def is_youtube_playlist(url: str) -> bool:
    """True se a URL é uma playlist do YouTube (tem parâmetro list= ou /playlist)."""
    if not is_youtube(url):
        return False
    u = url.lower()
    return ("list=" in u) or ("/playlist" in u)


# ==========================
# VALIDAÇÃO DE NOME DE ARQUIVO
# ==========================

# Caracteres proibidos em nomes de arquivo no Windows (e boa prática geral)
INVALID_FILENAME_CHARS = '\\/:*?"<>|'


def invalid_filename_chars(name: str):
    """Retorna a lista (ordenada, sem repetição) de caracteres proibidos presentes no nome."""
    if not name:
        return []
    found = []
    for c in name:
        if c in INVALID_FILENAME_CHARS and c not in found:
            found.append(c)
    return found


def is_valid_filename(name: str) -> bool:
    """True se o nome não tem caracteres proibidos e não é vazio."""
    return bool(name and name.strip()) and not invalid_filename_chars(name)


# ==========================
# NOMES DE ARQUIVO / CONFLITOS
# ==========================

def safe_filename(name: str) -> str:
    """Remove caracteres inválidos para filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", name or "").strip() or "video"


def expected_extension(format_type: str) -> str:
    """Extensão final esperada para o formato escolhido."""
    return "mp3" if (format_type or "").upper() == "MP3" else "mp4"


def expected_output_path(folder: str, title: str, format_type: str) -> str:
    """Caminho final previsto para o arquivo (pasta/título.ext)."""
    ext = expected_extension(format_type)
    return os.path.join(folder, f"{safe_filename(title)}.{ext}")


def file_conflict(folder: str, title: str, format_type: str) -> bool:
    """True se já existe um arquivo com mesmo nome e tipo na pasta."""
    return os.path.exists(expected_output_path(folder, title, format_type))


def resolve_unique_title(folder: str, title: str, format_type: str) -> str:
    """
    Retorna um título que não colida com arquivos existentes.
    Ex.: 'video' -> 'video (1)' -> 'video (2)' ...
    """
    base = safe_filename(title)
    if not file_conflict(folder, base, format_type):
        return base
    i = 1
    while True:
        candidate = f"{base} ({i})"
        if not file_conflict(folder, candidate, format_type):
            return candidate
        i += 1

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
def get_ffmpeg_exe():
    """Retorna o caminho completo do executável ffmpeg."""
    import sys as _sys
    bin_dir = get_ffmpeg_path()
    exe = "ffmpeg.exe" if _sys.platform == "win32" else "ffmpeg"
    full = os.path.join(bin_dir, exe)
    if os.path.exists(full):
        return full
    # fallback para ffmpeg do PATH
    return exe