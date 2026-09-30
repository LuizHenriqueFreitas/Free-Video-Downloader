# core/i18n.py

""" Here you will find:
    - supported languages and their display names;
    - current language get / set;
    - tr() - translate a text key to the current language;
    - language chosen on the installer (language.ini) and system language;
    - resolve_language() - decides which language the app starts with.

    The texts live in src/locales/<code>.py (one STRINGS dict per language).
    A key missing in a language falls back to DEFAULT_LANGUAGE, and a key
    missing everywhere shows the key itself - the UI never breaks.
"""

import configparser
import locale
import os
import sys

from locales import en, pt_BR

DEFAULT_LANGUAGE = "pt_BR"

# code -> STRINGS dict (import statically so PyInstaller bundles them)
_CATALOGS = {
    "pt_BR": pt_BR.STRINGS,
    "en": en.STRINGS,
}

# names shown on the language selector - always on their own language
LANGUAGE_NAMES = {
    "pt_BR": "Português (Brasil)",
    "en": "English",
}

SUPPORTED_LANGUAGES = tuple(_CATALOGS)

# file written by packaging/installer.iss next to GetMediaFree.exe
INSTALLER_LANGUAGE_FILE = "language.ini"

_current = DEFAULT_LANGUAGE


""" ==========================
    CURRENT LANGUAGE
  ========================== """

def get_language() -> str:
    return _current

def set_language(code):
    global _current
    _current = normalize_language(code) or DEFAULT_LANGUAGE


""" ==========================
    TRANSLATION
  ========================== """

# translate a key to the current language (or to "lang", when given)
# kwargs fill the "{placeholders}" of the text
def tr(key: str, lang=None, **kwargs) -> str:
    catalog = _CATALOGS.get(lang or _current, {})
    text = catalog.get(key)
    if text is None:
        text = _CATALOGS[DEFAULT_LANGUAGE].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


""" ==========================
    AUDIO TRACK LANGUAGE NAMES
  ========================== """

""" Name of an audio track language (yt-dlp code) in the app language:
    "pt" -> "Português" / "Portuguese". Order:
    1. the exact code ("pt-BR", "es-419", "zh-Hans");
    2. the base language + region ("de-AT" -> "Alemão (AT)");
    3. yt-dlp's description of the track (english), without its tags;
    4. the code itself.
"""
def audio_language_name(code, note="") -> str:
    catalog = _CATALOGS[DEFAULT_LANGUAGE]
    code = code or ""
    key = f"audio_lang.{code.lower()}"
    if key in catalog:
        return tr(key)

    base, _, region = code.partition("-")
    base_key = f"audio_lang.{base.lower()}"
    if base_key in catalog:
        name = tr(base_key)
        return f"{name} ({region.upper()})" if region else name

    # ex.: "Tamil, medium" / "Klingon original (default), medium" -> "Tamil" / "Klingon"
    described = (note or "").split(",")[0]
    for tag in ("(default)", "original", "- dubbed"):
        described = described.replace(tag, "")
    return described.strip() or code


""" ==========================
    LANGUAGE DETECTION
  ========================== """

# maps any known spelling to a supported code, None if unknown
# (Inno Setup names, "pt-BR", "pt_BR.UTF-8", Windows "Portuguese_Brazil", ...)
def normalize_language(value):
    if not value:
        return None
    v = str(value).strip().lower().replace("-", "_")
    if v in ("pt_br", "brazilianportuguese") or v.startswith(("pt", "portuguese")):
        return "pt_BR"
    if v.startswith(("en", "english")):
        return "en"
    return None

# language chosen on the installer, None if not installed (dev mode) or unreadable
def get_installer_language():
    if not getattr(sys, "frozen", False):
        return None
    path = os.path.join(os.path.dirname(sys.executable), INSTALLER_LANGUAGE_FILE)
    if not os.path.exists(path):
        return None
    try:
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8-sig")
        return normalize_language(parser.get("Settings", "Language", fallback=None))
    except Exception:
        return None

# operating system language, None if not supported
def get_system_language():
    try:
        return normalize_language(locale.getlocale()[0])
    except Exception:
        return None


""" The language the app starts with. Priority:
    1. saved on settings.json (chosen on the app selector);
    2. chosen on the installer;
    3. operating system language;
    4. DEFAULT_LANGUAGE.
    A new installer choice (reinstall with another language) replaces the
    saved one, so the latest explicit choice always wins.
"""
def resolve_language(settings) -> str:
    installed = get_installer_language()
    if installed and installed != settings.get_installer_language():
        settings.set_installer_language(installed)
        settings.set_language(installed)

    return (
        normalize_language(settings.get_language())
        or installed
        or get_system_language()
        or DEFAULT_LANGUAGE
    )
