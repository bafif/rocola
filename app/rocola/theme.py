"""Branding/tema: colores, fuentes y logo cargados desde assets/themes/<tema>.

El código nunca hardcodea estética: todo sale de theme.toml (con fallbacks
seguros si falta el archivo, una fuente o el logo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pygame

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

Color = tuple[int, int, int]

_DEFAULTS: dict[str, Color] = {
    "background": (11, 11, 21),
    "accent": (255, 51, 102),
    "text": (245, 245, 245),
    "highlight": (255, 210, 74),
    "muted": (120, 120, 160),
}


def _hex(value: str | None, default: Color) -> Color:
    s = (value or "").lstrip("#")
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            return default
    return default


@dataclass
class Theme:
    name: str = "default"
    title: str = "ROCOLA"
    colors: dict[str, Color] = field(default_factory=lambda: dict(_DEFAULTS))
    logo_path: Path | None = None
    _font_files: dict[str, Path | None] = field(default_factory=dict)
    _font_cache: dict = field(default_factory=dict)
    _logo_cache: dict = field(default_factory=dict)

    @classmethod
    def load(cls, theme_dir: Path) -> "Theme":
        data: dict = {}
        cfg = theme_dir / "theme.toml"
        if tomllib is not None and cfg.is_file():
            try:
                data = tomllib.loads(cfg.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                data = {}

        colors_raw = data.get("colors", {})
        colors = {name: _hex(colors_raw.get(name), default) for name, default in _DEFAULTS.items()}

        branding = data.get("branding", {})
        logo = branding.get("logo")
        fonts = data.get("fonts", {})

        return cls(
            name=data.get("name", "default"),
            title=branding.get("title", "ROCOLA"),
            colors=colors,
            logo_path=(theme_dir / logo).resolve() if logo else None,
            _font_files={
                "title": (theme_dir / fonts["title"]) if fonts.get("title") else None,
                "body": (theme_dir / fonts["body"]) if fonts.get("body") else None,
            },
        )

    def color(self, name: str) -> Color:
        return self.colors.get(name, (255, 255, 255))

    def font(self, role: str = "body", size: int = 24) -> "pygame.font.Font":
        key = (role, size)
        if key in self._font_cache:
            return self._font_cache[key]
        path = self._font_files.get(role)
        try:
            if path and path.is_file():
                font = pygame.font.Font(str(path), size)
            else:
                font = pygame.font.Font(None, size)
        except (OSError, pygame.error):
            font = pygame.font.Font(None, size)
        self._font_cache[key] = font
        return font

    def logo(self, max_height: int | None = None):
        if not self.logo_path or not self.logo_path.is_file():
            return None
        key = max_height or 0
        if key in self._logo_cache:
            return self._logo_cache[key]
        try:
            img = pygame.image.load(str(self.logo_path)).convert_alpha()
        except (OSError, pygame.error):
            self._logo_cache[key] = None
            return None
        if max_height and img.get_height() > max_height:
            scale = max_height / img.get_height()
            img = pygame.transform.smoothscale(
                img, (int(img.get_width() * scale), max_height)
            )
        self._logo_cache[key] = img
        return img
