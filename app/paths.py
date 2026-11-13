"""Rutas de datos y recursos compartidas por la app y el lanzador."""

import os
import sys
from pathlib import Path

APP_NAME = "JobTracker"


def _platform_data_root() -> Path:
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA")
        return Path(base) if base else Path.home() / "AppData" / "Local"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    base = os.getenv("XDG_DATA_HOME")
    return Path(base) if base else Path.home() / ".local" / "share"


def data_dir() -> Path:
    """Carpeta de datos del usuario. Nunca dentro de la carpeta del programa."""
    override = os.getenv("JOBTRACKER_DATA_DIR")
    path = Path(override).expanduser() if override else _platform_data_root() / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "jobtracker.db"


def resource_dir() -> Path:
    """Raíz de recursos: ``_internal`` con PyInstaller, repo en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource(*parts: str) -> Path:
    return resource_dir().joinpath(*parts)
