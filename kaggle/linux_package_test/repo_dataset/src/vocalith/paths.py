"""Per-OS user data dirs. Never write into the install directory (Program Files, a
read-only macOS app bundle, etc. are not writable)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from platformdirs import user_data_dir
except ImportError:  # pragma: no cover - platformdirs is a hard dependency at runtime
    user_data_dir = None

APP_NAME = "Vocalith"


def _base_dir() -> Path:
    if user_data_dir is not None:
        return Path(user_data_dir(APP_NAME, appauthor=False))
    # fallback if platformdirs isn't installed yet (e.g. during bootstrap)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
    return Path.home() / f".local/share/{APP_NAME.lower()}"


def models_dir() -> Path:
    p = _base_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def outputs_dir() -> Path:
    p = _base_dir() / "outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = _base_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = _base_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def configure_hf_home() -> None:
    """Route HuggingFace's own cache into our models dir so a reinstall doesn't
    re-download everything, and so weights aren't buried in the Python install."""
    os.environ.setdefault("HF_HOME", str(models_dir() / "hf"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
