# core/utils.py

import sys
import os
import re
import stat
import shutil

# ==========================
# PLATAFORM / URL
# ==========================

# domains -> nomalize plataform diferent names
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
    """Identify the plataform using current URL. Retorn 'generic' if unknow."""
    if not url:
        return "generic"
    u = url.lower()
    for platform, domains in _PLATFORM_DOMAINS.items():
        if any(d in u for d in domains):
            return platform
    return "generic"


def looks_like_url(text: str) -> bool:
    """verify if looks like a https link"""
    if not text:
        return False
    return bool(re.search(r"https?://[^\s]+", text.strip()))

# bool function - verify if the plataform is youtube
def is_youtube(url: str) -> bool:
    return detect_platform(url) == "youtube"

# bool function - verify if is a youtube playlis using url parameters
def is_youtube_playlist(url: str) -> bool:
    """True if the URL was a playlist from YouTube (with parameter list= or /playlist on the url)."""
    if not is_youtube(url):
        return False
    u = url.lower()
    return ("list=" in u) or ("/playlist" in u)


# ==========================
# FILE NAME VALIDATION
# ==========================

# Windows file name blocked characters
INVALID_FILENAME_CHARS = '\\/:*?"<>|'

# searche for blocked characters at the file name
def invalid_filename_chars(name: str):
    """Retorn a list (ordened, loopout) of blocked caracters at the file name."""
    if not name:
        return []
    found = []
    for c in name:
        if c in INVALID_FILENAME_CHARS and c not in found:
            found.append(c)
    return found


def is_valid_filename(name: str) -> bool:
    """True is has no blocked characters and is not null."""
    return bool(name and name.strip()) and not invalid_filename_chars(name)


# ==========================
# FILE NAMES / CONFLICTS
# ==========================

def safe_filename(name: str) -> str:
    """Remove invalid caracters to file names."""
    return re.sub(r'[\\/*?:"<>|]', "", name or "").strip() or "video"


def expected_extension(format_type: str) -> str:
    """Final extension for the format choiced."""
    return "mp3" if (format_type or "").upper() == "MP3" else "mp4"


def expected_output_path(folder: str, title: str, format_type: str) -> str:
    """Probably file last path (folder/title.ext)."""
    ext = expected_extension(format_type)
    return os.path.join(folder, f"{safe_filename(title)}.{ext}")

# verify duplicated names and type
def file_conflict(folder: str, title: str, format_type: str) -> bool:
    """True if has another file with same name and type at same folder."""
    return os.path.exists(expected_output_path(folder, title, format_type))


def resolve_unique_title(folder: str, title: str, format_type: str) -> str:
    """
    Return a alternative title different of other arquives.
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
# USER DATA FOLDER (persistence)
# ==========================

def get_user_data_dir():
    """
    Return the directory where stay the user data (cookies, history, etc.)
    At development: ./data
    At executable: acessible on folder 'data', near the .exe
    """
    if getattr(sys, 'frozen', False):
        # Executable: uses .exe owne directory
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(".")
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

# ==========================
# INTERNAL RESOURCES (packed on .exe)
# ==========================

def resource_path(relative_path):
    """
    Return the correct path to internal resources (bin, tools, assets)
    that will be packed inside executable (only read).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_ytdlp_path():
    if sys.platform == "win32":
        return resource_path("bin/yt-dlp.exe")
    else:
        # Tenta encontrar no sistema primeiro
        yt_dlp = shutil.which('yt-dlp')
        if yt_dlp:
            return yt_dlp
        
        raise Exception("yt-dlp não encontrado. Instale com: pip install yt-dlp")

def get_ffmpeg_path():
    if sys.platform == "win32":
        return resource_path("tools/ffmpeg/bin/")
    else:
        # Usa o ffmpeg do sistema
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        
        raise Exception("FFmpeg não encontrado. Instale com: sudo apt install ffmpeg")

def get_node_path():
    """
    Retorna o caminho do Node.js de forma flexível para Windows e Linux
    """
    if sys.platform == "win32":
        # Windows: procura no projeto primeiro
        node_paths = [
            resource_path("bin/node/node.exe"),  # Seu caminho atual
            resource_path("node.exe"),           # Fallback
            "node.exe",                          # Sistema
            "node"                               # Último recurso
        ]
    else:
        # Linux/macOS: procura no sistema primeiro
        node = shutil.which('node')
        if node:
            return node
    
    raise Exception(
        "Node.js não encontrado!\n Linux: Instale com 'sudo apt install nodejs' ou use nvm"
    )


# ==========================
# COOKIES (user data)
# ==========================

def get_cookies_path():
    """Caminho para o arquivo de cookies (dentro do diretório de dados do usuário)."""
    return os.path.join(get_user_data_dir(), "cookies.txt")

def cookies_exists():
    return os.path.exists(get_cookies_path())

def secure_cookies_file(path: str):
    """Configure permissions to this file (Unix: 600, Windows: readonly)."""
    if not os.path.exists(path):
        return
    try:
        # Unix-like: only the owner read/write
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except:
        # Windows: try to turn just read
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
    """Return the complete path to ffmpeg executable."""
    import sys as _sys
    bin_dir = get_ffmpeg_path()
    exe = "ffmpeg.exe" if _sys.platform == "win32" else "ffmpeg"
    full = os.path.join(bin_dir, exe)
    if os.path.exists(full):
        return full
    # fallback for ffmpeg of PATH
    return exe