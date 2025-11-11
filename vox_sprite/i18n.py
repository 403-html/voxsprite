from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

DEFAULT_LANG = "en"
TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"
_current_lang = os.getenv("VOXSPRITE_LANG", DEFAULT_LANG)


@lru_cache(maxsize=None)
def _load_lang(lang: str) -> dict[str, str]:
    path = TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        path = TRANSLATIONS_DIR / f"{DEFAULT_LANG}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def t(key: str, **kwargs) -> str:
    data = _load_lang(_current_lang)
    text = data.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def set_language(lang: str) -> str:
    global _current_lang
    if not (TRANSLATIONS_DIR / f"{lang}.json").exists():
        lang = DEFAULT_LANG
    _current_lang = lang
    _load_lang.cache_clear()
    return _current_lang


def current_language() -> str:
    return _current_lang


def available_languages() -> dict[str, str]:
    langs: dict[str, str] = {}
    for path in sorted(TRANSLATIONS_DIR.glob("*.json")):
        code = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        name = data.get("language.name", code.upper())
        langs[code] = name
    return langs or {DEFAULT_LANG: DEFAULT_LANG.upper()}
