"""Configuración de la rocola: valores por defecto + overrides por entorno/archivo."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

# Rutas estándar dentro del SO instalado.
ASSETS_DIR = Path(os.environ.get("ROCOLA_ASSETS", Path(__file__).resolve().parent.parent / "assets"))
USER_CONFIG = Path(os.environ.get("ROCOLA_CONFIG", "/etc/rocola/rocola.toml"))


def _parse_res(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except ValueError:
        return None


@dataclass
class Config:
    mpd_host: str = "127.0.0.1"
    mpd_port: int = 6600
    theme: str = "default"
    # None => pantalla completa al modo nativo. Forzar p. ej. (640, 480) para CRT/pruebas.
    resolution: tuple[int, int] | None = None
    windowed: bool = False
    fps: int = 30
    music_dir: str = "/music"

    # Combo de teclas para abrir el instalador (ver input.py / docs 06).
    installer_hotkey: str = "F10"

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        # 1) archivo de usuario (si existe y hay tomllib)
        if tomllib is not None and USER_CONFIG.is_file():
            try:
                data = tomllib.loads(USER_CONFIG.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                data = {}
            for key, val in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, val)
        # 2) overrides por entorno (prioridad máxima, útil en dev)
        cfg.mpd_host = os.environ.get("ROCOLA_MPD_HOST", cfg.mpd_host)
        cfg.mpd_port = int(os.environ.get("ROCOLA_MPD_PORT", cfg.mpd_port))
        cfg.theme = os.environ.get("ROCOLA_THEME", cfg.theme)
        cfg.windowed = os.environ.get("ROCOLA_WINDOWED", "1" if cfg.windowed else "0") == "1"
        res = _parse_res(os.environ.get("ROCOLA_RES"))
        if res:
            cfg.resolution = res
        return cfg

    @property
    def theme_dir(self) -> Path:
        return ASSETS_DIR / "themes" / self.theme
