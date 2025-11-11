from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

APP_VERSION = "1.0.0"
BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = Path("voice_reactor.json")

def _bundle_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return BASE_DIR

def resource_path(*parts: str) -> Path:
    search_roots = [_bundle_root(), BASE_DIR, Path.cwd()]
    for root in search_roots:
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return search_roots[0].joinpath(*parts)


DEFAULT_CFG: dict[str, Any] = {
    "idle_image": "",
    "talk_image": "",
    "talk_frames": [],
    "bg": "#00FF00",
    "bg_transparent": False,
    "width": 512,
    "talk_th": 0.03,
    "keep_on_top": False,
    "drag_enabled": True,
    "idle_frames": [],
    "idle_anim_random": False,
    "idle_interval_min": 0.2,
    "idle_interval_max": 0.6,
    "language": "en",
    "remember_position": False,
    "avatar_position": [],
}


def load_cfg() -> dict[str, Any]:
    loaded_config = DEFAULT_CFG.copy()
    try:
        if SETTINGS_FILE.exists():
            loaded_config.update(json.loads(SETTINGS_FILE.read_text()))
    except Exception:
        pass
    return loaded_config


def save_cfg(values: dict[str, Any]) -> None:
    data = {
        "idle_image": str(values.get("idle_image", "")),
        "talk_image": str(values.get("talk_image", "")),
        "talk_frames": list(values.get("talk_frames", [])),
        "bg": values["bg"],
        "bg_transparent": bool(values.get("bg_transparent", False)),
        "width": int(values["width"]),
        "talk_th": float(values["talk_th"]),
        "keep_on_top": bool(values["keep_on_top"]),
        "drag_enabled": bool(values["drag_enabled"]),
        "idle_frames": list(values.get("idle_frames", [])),
        "idle_anim_random": bool(values.get("idle_anim_random", False)),
        "idle_interval_min": float(values.get("idle_interval_min", 0.2)),
        "idle_interval_max": float(values.get("idle_interval_max", 0.6)),
        "language": str(values.get("language", "en")),
        "remember_position": bool(values.get("remember_position", False)),
        "avatar_position": list(values.get("avatar_position", [])),
    }
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))
