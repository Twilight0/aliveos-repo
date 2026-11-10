"""
Persistent configuration management for orangepi-config (/etc/default/orangepi-config).
"""

from __future__ import annotations

import os
import shlex
import sys
from typing import Dict

SYSTEM_CONFIG_PATH = "/etc/default/orangepi-config"
USER_CONFIG_PATH = os.path.expanduser("~/.config/orangepi-config/config")
DEFAULT_WINDOW_TITLE = "Orange Pi Zero — orangepi-config"


def _get_readable_config_path() -> str:
    if os.path.exists(SYSTEM_CONFIG_PATH):
        return SYSTEM_CONFIG_PATH
    if os.path.exists(USER_CONFIG_PATH):
        return USER_CONFIG_PATH
    return SYSTEM_CONFIG_PATH


def _get_writable_config_path() -> str:
    if os.geteuid() == 0 or (
        os.path.exists(SYSTEM_CONFIG_PATH) and os.access(SYSTEM_CONFIG_PATH, os.W_OK)
    ) or os.access(os.path.dirname(SYSTEM_CONFIG_PATH), os.W_OK):
        return SYSTEM_CONFIG_PATH
    return USER_CONFIG_PATH


def load_config() -> Dict[str, str]:
    """Reads key=value settings from /etc/default/orangepi-config."""
    cfg: Dict[str, str] = {}
    path = _get_readable_config_path()
    if not os.path.exists(path):
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                try:
                    parts = shlex.split(val)
                    cfg[key] = parts[0] if parts else ""
                except ValueError:
                    cfg[key] = val.strip("\"'")
    except Exception:
        pass
    return cfg


def save_config_key(key: str, value: str) -> str:
    """Saves or updates a key=value entry in /etc/default/orangepi-config. Returns path written."""
    path = _get_writable_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    new_entry = f'{key}="{escaped}"\n'
    updated = False
    out_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                out_lines.append(new_entry)
                updated = True
                continue
        out_lines.append(line)

    if not updated:
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] += "\n"
        out_lines.append(new_entry)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    return path


def get_window_title() -> str:
    """Returns the configured custom window/web-tab title, or DEFAULT_WINDOW_TITLE."""
    env_title = os.environ.get("ORANGEPI_CONFIG_TITLE", "").strip()
    if env_title:
        return env_title
    cfg = load_config()
    title = cfg.get("WINDOW_TITLE", "").strip()
    return title if title else DEFAULT_WINDOW_TITLE


def set_window_title(title: str) -> str:
    """Persists the custom window/web-tab title and returns the config file path."""
    clean_title = title.strip() or DEFAULT_WINDOW_TITLE
    return save_config_key("WINDOW_TITLE", clean_title)


def emit_terminal_title(title: str) -> None:
    """Emits XTerm/ttyd OSC 0 and OSC 2 escape sequences to set the browser/terminal window title."""
    clean = title.replace("\033", "").replace("\007", "").strip() or DEFAULT_WINDOW_TITLE
    try:
        sys.stdout.write(f"\033]0;{clean}\007\033]2;{clean}\007")
        sys.stdout.flush()
    except Exception:
        pass
