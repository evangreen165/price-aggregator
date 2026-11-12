"""Application configuration and path resolution."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

APP_NAME = "Price Aggregator"
HOST = "127.0.0.1"
PORT = 8000

IS_FROZEN = bool(getattr(sys, "frozen", False))

_CONFIG_FILE = Path(__file__).resolve()
BASE_DIR = _CONFIG_FILE.parents[3] if len(_CONFIG_FILE.parents) > 3 else _CONFIG_FILE.parents[2]
BACKEND_DIR = BASE_DIR / "backend"


def resource_path(rel: str) -> Path:
    """Resolve a bundled resource path, honouring PyInstaller's temp extraction dir."""
    if IS_FROZEN:
        base = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    else:
        base = BASE_DIR
    return base / rel


FRONTEND_DIST = resource_path("frontend/dist")
PLUGINS_DIR = resource_path("backend/plugins")
LOG_FILE = Path(tempfile.gettempdir()) / "price_aggregator.log"
