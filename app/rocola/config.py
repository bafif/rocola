"""Configuración de la rocola: valores por defecto + overrides por entorno/archivo."""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

# Rutas estándar dentro del SO instalado.
ASSETS_DIR = Path(
    os.environ.get("ROCOLA_ASSETS", Path(__file__).resolve().parent.parent / "assets")
)
USER_CONFIG = Path(os.environ.get("ROCOLA_CONFIG", "/etc/rocola/rocola.toml"))


def _parse_res(value: object) -> tuple[int, int] | None:
    """Accept "640x480" (env/TOML string) or [640, 480] (TOML array); None if invalid."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            w, h = value.lower().split("x")
        elif isinstance(value, (list, tuple)):
            w, h = value
        else:
            return None
        res = int(w), int(h)
    except (TypeError, ValueError):
        return None
    return res if res[0] > 0 and res[1] > 0 else None


def _parse_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default


def _parse_map(value: object, *, int_keys: bool) -> dict:
    """The [keys] / [buttons] tables of rocola.toml: {key name or button index: action}.

    Entries that are not strings (or, for buttons, not a non-negative index) are dropped
    here; unknown key names and actions are dropped later by the input layer.
    """
    if not isinstance(value, dict):
        return {}
    out: dict = {}
    for key, action in value.items():
        if not isinstance(action, str):
            continue
        if int_keys:
            try:
                key = int(key)
            except (TypeError, ValueError):
                continue
            if key < 0:
                continue
        out[key] = action.strip().lower()
    return out


def _coerce(name: str, value: object, current: object) -> object:
    """Coerce a value from rocola.toml to the field's type, keeping the current one if invalid.

    A bad value in /etc/rocola/rocola.toml must never crash the app at boot (the kiosk
    would stay on a black screen), so anything that does not fit falls back.
    """
    if name == "resolution":
        return _parse_res(value)
    if name in ("keys", "buttons"):
        return _parse_map(value, int_keys=name == "buttons")
    if isinstance(current, bool):
        return value if isinstance(value, bool) else current
    if isinstance(current, int):
        return _parse_int(value, current)
    if name == "screenshot":
        return value if isinstance(value, str) and value else None
    return value if isinstance(value, str) else current


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

    # Mapeos de controles que se suman a los de input.py (tablas [keys] y [buttons] de
    # rocola.toml; ver docs 06): nombre de tecla SDL o índice de botón -> acción.
    keys: dict[str, str] = field(default_factory=dict)
    buttons: dict[int, str] = field(default_factory=dict)

    # Modo captura (dev/CI): si ROCOLA_SCREENSHOT apunta a un archivo, la app
    # renderiza unos frames, guarda un PNG y sale. Sirve para previews del
    # branding y para verificar el render sin hardware/monitor real.
    screenshot: str | None = None
    screenshot_scene: str = "library"

    @classmethod
    def load(cls) -> Config:
        cfg = cls()
        # 1) archivo de usuario (si existe y hay tomllib)
        if tomllib is not None and USER_CONFIG.is_file():
            try:
                data = tomllib.loads(USER_CONFIG.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                data = {}
            known = {f.name for f in fields(cfg)}
            for key, val in data.items():
                if key in known:
                    setattr(cfg, key, _coerce(key, val, getattr(cfg, key)))
        # 2) overrides por entorno (prioridad máxima, útil en dev)
        cfg.mpd_host = os.environ.get("ROCOLA_MPD_HOST", cfg.mpd_host)
        cfg.mpd_port = _parse_int(os.environ.get("ROCOLA_MPD_PORT", cfg.mpd_port), cfg.mpd_port)
        cfg.theme = os.environ.get("ROCOLA_THEME", cfg.theme)
        cfg.windowed = os.environ.get("ROCOLA_WINDOWED", "1" if cfg.windowed else "0") == "1"
        res = _parse_res(os.environ.get("ROCOLA_RES"))
        if res:
            cfg.resolution = res
        cfg.screenshot = os.environ.get("ROCOLA_SCREENSHOT", cfg.screenshot)
        cfg.screenshot_scene = os.environ.get("ROCOLA_SCREENSHOT_SCENE", cfg.screenshot_scene)
        return cfg

    @property
    def theme_dir(self) -> Path:
        return ASSETS_DIR / "themes" / self.theme
