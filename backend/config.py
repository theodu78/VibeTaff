"""
Application settings — personal / enterprise profiles.

Settings are stored in ~/.vibetaff/settings.json.
Every setting has a sensible default (personal profile).
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SETTINGS_DIR = Path.home() / ".vibetaff"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "profile": "personal",

    "llm.provider": "deepseek",
    "llm.model": "deepseek-chat",

    "security.allow_code_execution": True,
    "security.sandbox_mode": "restricted",
    "security.approval_all_tools": False,
    "security.log_export_url": None,

    "tools.dynamic_injection": False,
    "tools.disabled_tools": [],
    "tools.disabled_categories": [],

    "ui.show_thinking": True,
    "ui.language": "fr",
}

ENTERPRISE_PRESET: dict[str, Any] = {
    "profile": "enterprise",
    "security.allow_code_execution": False,
    "security.sandbox_mode": "subprocess",
    "security.approval_all_tools": True,
    "tools.dynamic_injection": True,
    "tools.disabled_tools": ["run_local_calculation"],
}

PERSONAL_PRESET: dict[str, Any] = {
    "profile": "personal",
    "security.allow_code_execution": True,
    "security.sandbox_mode": "restricted",
    "security.approval_all_tools": False,
    "tools.dynamic_injection": False,
    "tools.disabled_tools": [],
}

_cache: dict[str, Any] = {}


def _load() -> dict[str, Any]:
    global _cache
    if _cache:
        return _cache
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_FILE.exists():
        try:
            _cache = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return _cache
        except Exception as e:
            logger.warning(f"Cannot read settings: {e}")
    _cache = {}
    return _cache


def _save():
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(_cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get(key: str, default: Any = None) -> Any:
    data = _load()
    if key in data:
        return data[key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    return default


def set_value(key: str, value: Any):
    _load()
    _cache[key] = value
    _save()


def set_many(updates: dict[str, Any]):
    _load()
    _cache.update(updates)
    _save()


def apply_preset(preset_name: str) -> dict[str, Any]:
    if preset_name == "enterprise":
        preset = ENTERPRISE_PRESET
    else:
        preset = PERSONAL_PRESET
    _load()
    _cache.update(preset)
    _save()
    return get_all()


def get_all() -> dict[str, Any]:
    data = _load()
    merged = {**DEFAULTS, **data}
    return merged


def reload():
    global _cache
    _cache = {}
    _load()
