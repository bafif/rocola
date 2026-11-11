"""Theme engine v2: what every screen looks like comes from assets/themes/<theme>/theme.toml.

A theme sets fixed color roles, four fonts (marquee, strip, body, digits), pieces (PNG images,
optionally with nine-slice cuts), effects with their parameters, and one variant per kind of
display (lcd, crt, crt15, tv) laid over the base. Everything is optional: a missing piece is
drawn with the colors, a missing font falls back to another role or to SDL's own, a missing
or broken theme is black and white, and nothing in a theme can keep the jukebox from starting.
The scenes never name a color value or a file: they ask the theme.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from .config import ASSETS_DIR

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore

Color = tuple[int, int, int]

# Black and white: what a missing or broken theme looks like.
FALLBACK_COLORS: dict[str, Color] = {
    "background": (0, 0, 0),  # behind everything: the cabinet
    "surface": (255, 255, 255),  # title cards and panels
    "text": (0, 0, 0),  # text on the surface
    "text_dim": (85, 85, 85),
    "on_dark": (255, 255, 255),  # text on the background
    "on_dark_dim": (170, 170, 170),
    "accent": (0, 0, 0),  # stripes and codes on the cards
    "glow": (255, 255, 255),  # cursor and lamps
}
ROLES = tuple(FALLBACK_COLORS)
# A dim role the theme leaves out is mixed from its pair: (color, over, how much of color).
_DERIVED = {
    "text_dim": ("text", "surface", 0.6),
    "on_dark_dim": ("on_dark", "background", 0.6),
}

FONT_ROLES = ("marquee", "strip", "body", "digits")
# Where a role looks when the theme has no file for it; after these, SDL's own font.
_FONT_FALLBACK = {
    "marquee": ("strip", "body"),
    "strip": ("body",),
    "digits": ("body",),
    "body": (),
}


@dataclass(frozen=True)
class DisplayProfile:
    """What a kind of display asks of every theme (docs/09, «Variantes por tipo de pantalla»)."""

    safe_area: float  # margin on each side, as a fraction of the screen
    min_font: int  # smallest text, in pixels
    cards: tuple[int, int]  # title cards per page: columns, rows
    min_contrast: float  # text against what is behind it (WCAG ratio)
    min_luma_gap: float  # text and what is behind it apart by this much of the luminance scale


PROFILES: dict[str, DisplayProfile] = {
    "lcd": DisplayProfile(0.03, 18, (2, 5), 4.5, 0.0),
    "crt": DisplayProfile(0.05, 16, (2, 4), 4.5, 0.0),
    "crt15": DisplayProfile(0.08, 10, (2, 3), 7.0, 0.0),
    "tv": DisplayProfile(0.10, 14, (2, 3), 4.5, 0.5),
}


def parse_color(value: object, default: Color) -> Color:
    """ "#rrggbb" (or "rrggbb") as a color; `default` for anything else."""
    s = value.lstrip("#") if isinstance(value, str) else ""
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            return default
    return default


def mix(a: Color, b: Color, amount: float) -> Color:
    """`amount` of `a` over `b`: 1 is all `a`, 0 is all `b`."""
    return tuple(round(x * amount + y * (1 - amount)) for x, y in zip(a, b))  # type: ignore[return-value]


def _merge(base: dict, variant: dict) -> dict:
    """Lay a variant over the base: tables merge key by key, anything else is replaced.

    Only one level deep: `fonts.body` in a variant replaces the base body font and keeps the
    others, but a piece or an effect is replaced whole (a 240p piece has its own cuts).
    """
    out = dict(base)
    for key, value in variant.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
        else:
            out[key] = value
    return out


def _table(data: dict, name: str) -> dict:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def _resolve(theme_dir: Path, rel: object) -> Path | None:
    """A file named in the theme: next to theme.toml, else under assets/ (shared fonts)."""
    if not isinstance(rel, str) or not rel:
        return None
    for base in (theme_dir, ASSETS_DIR):
        candidate = base / rel
        if candidate.is_file():
            return candidate
    return None


def _slice(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in value):
        return None
    return (value[0], value[1], value[2], value[3])


@dataclass
class Piece:
    """An image of the theme, with its nine-slice cuts (left, top, right, bottom) if it has them."""

    image: pygame.Surface
    slice: tuple[int, int, int, int] | None = None
    _sizes: dict = field(default_factory=dict, repr=False)

    def render(self, width: int, height: int) -> pygame.Surface:
        """The piece at width×height: corners as drawn, edges and middle stretched to fit."""
        size = (max(1, width), max(1, height))
        if size in self._sizes:
            return self._sizes[size]
        if len(self._sizes) >= 32:  # one per size on screen; a resize must not pile them up
            self._sizes.clear()
        img = self.image
        iw, ih = img.get_size()
        if (iw, ih) == size:
            out = img
        elif self.slice is None or not self._fits(size):
            out = pygame.transform.scale(img, size)
        else:
            out = self._nine_slice(size)
        self._sizes[size] = out
        return out

    def _fits(self, size: tuple[int, int]) -> bool:
        left, top, right, bottom = self.slice  # type: ignore[misc]
        iw, ih = self.image.get_size()
        return left + right <= min(iw, size[0]) and top + bottom <= min(ih, size[1])

    def _nine_slice(self, size: tuple[int, int]) -> pygame.Surface:
        img = self.image
        iw, ih = img.get_size()
        left, top, right, bottom = self.slice  # type: ignore[misc]
        w, h = size
        src_x, src_y = (0, left, iw - right, iw), (0, top, ih - bottom, ih)
        dst_x, dst_y = (0, left, w - right, w), (0, top, h - bottom, h)
        out = pygame.Surface(size, img.get_flags() & pygame.SRCALPHA, img)
        for i in range(3):
            for j in range(3):
                sw, sh = src_x[i + 1] - src_x[i], src_y[j + 1] - src_y[j]
                dw, dh = dst_x[i + 1] - dst_x[i], dst_y[j + 1] - dst_y[j]
                if min(sw, sh, dw, dh) <= 0:
                    continue
                part = img.subsurface((src_x[i], src_y[j], sw, sh))
                if (sw, sh) != (dw, dh):
                    part = pygame.transform.scale(part, (dw, dh))
                out.blit(part, (dst_x[i], dst_y[j]))
        return out


@dataclass
class Theme:
    name: str = "Rocola"
    display: str = "lcd"
    # A plain string, or one per language: { es = "MI ROCOLA", en = "MY JUKEBOX" }.
    title: str | dict[str, str] = "ROCOLA"
    colors: dict[str, Color] = field(default_factory=lambda: dict(FALLBACK_COLORS))
    effects: dict = field(default_factory=dict)
    safe_area: float = PROFILES["lcd"].safe_area
    antialias: bool = True
    _fonts: dict[str, Path | None] = field(default_factory=dict, repr=False)
    _pieces: dict[str, tuple[Path, tuple | None]] = field(default_factory=dict, repr=False)
    _font_cache: dict = field(default_factory=dict, repr=False)
    _piece_cache: dict = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, theme_dir: Path, display: str = "lcd") -> Theme:
        display = display if display in PROFILES else "lcd"
        try:
            return cls._from_data(_read(theme_dir / "theme.toml"), theme_dir, display)
        except Exception as exc:  # noqa: BLE001 — a theme must never stop the jukebox
            print(f"[rocola] theme {theme_dir.name}: {exc}; black and white", file=sys.stderr)
            return cls(display=display, safe_area=PROFILES[display].safe_area)

    @classmethod
    def _from_data(cls, data: dict, theme_dir: Path, display: str) -> Theme:
        variant = _table(_table(data, "variant"), display)
        if variant:
            data = _merge(data, variant)

        raw = _table(data, "colors")
        colors = {
            role: parse_color(raw.get(role), FALLBACK_COLORS[role])
            for role in ROLES
            if role not in _DERIVED
        }
        for role, (src, over, amount) in _DERIVED.items():
            given = parse_color(raw.get(role), (-1, -1, -1))
            if given != (-1, -1, -1):
                colors[role] = given
            elif src in raw or over in raw:
                colors[role] = mix(colors[src], colors[over], amount)
            else:
                colors[role] = FALLBACK_COLORS[role]

        fonts = _table(data, "fonts")
        pieces: dict[str, tuple[Path, tuple | None]] = {}
        for name, value in _table(data, "pieces").items():
            spec = value if isinstance(value, dict) else {"file": value}
            path = _resolve(theme_dir, spec.get("file"))
            if path is not None:
                pieces[name] = (path, _slice(spec.get("slice")))

        safe = data.get("safe_area")
        if not isinstance(safe, (int, float)) or isinstance(safe, bool) or not 0 <= safe <= 0.25:
            safe = PROFILES[display].safe_area
        name = data.get("name")
        branding = _table(data, "branding")
        antialias = fonts.get("antialias", True)
        return cls(
            name=name if isinstance(name, str) and name else theme_dir.name,
            display=display,
            title=branding.get("title", "ROCOLA"),
            colors=colors,
            effects=dict(_table(data, "effects")),
            safe_area=float(safe),
            antialias=antialias if isinstance(antialias, bool) else True,
            _fonts={role: _resolve(theme_dir, fonts.get(role)) for role in FONT_ROLES},
            _pieces=pieces,
        )

    # --- lo que el tema le dice a la pantalla -------------------------------
    @property
    def profile(self) -> DisplayProfile:
        return PROFILES[self.display]

    def title_for(self, lang: str) -> str:
        """The marquee title in `lang`: the theme's own text for it, else its first one."""
        if isinstance(self.title, dict):
            texts = [str(v) for v in self.title.values() if v]
            return str(self.title.get(lang) or (texts[0] if texts else "ROCOLA"))
        return str(self.title)

    def color(self, role: str) -> Color:
        return self.colors.get(role, (255, 255, 255))

    def font(self, role: str = "body", size: int = 24) -> pygame.font.Font:
        """The font for `role`, never smaller than the display's minimum."""
        size = max(size, self.profile.min_font)
        key = (role, size)
        if key in self._font_cache:
            return self._font_cache[key]
        path = None
        for candidate in (role, *_FONT_FALLBACK.get(role, ("body",))):
            path = self._fonts.get(candidate)
            if path is not None:
                break
        try:
            font = pygame.font.Font(str(path) if path else None, size)
        except (OSError, pygame.error):
            font = pygame.font.Font(None, size)
        self._font_cache[key] = font
        return font

    def piece(self, name: str) -> Piece | None:
        """The theme's image called `name`, converted for the screen; None to draw it in colors."""
        if name in self._piece_cache:
            return self._piece_cache[name]
        piece = None
        spec = self._pieces.get(name)
        if spec is not None:
            try:
                img = pygame.image.load(str(spec[0]))
                if pygame.display.get_surface() is not None:  # match the framebuffer once
                    has_alpha = img.get_flags() & pygame.SRCALPHA
                    img = img.convert_alpha() if has_alpha else img.convert()
                piece = Piece(img, spec[1])
            except (OSError, pygame.error) as exc:
                print(f"[rocola] theme {self.name}: piece {name}: {exc}", file=sys.stderr)
        self._piece_cache[name] = piece
        return piece

    def effect(self, name: str, default: object = None) -> object:
        """An effect's parameters as the theme wrote them (a table, a word or a number)."""
        return self.effects.get(name, default)

    def safe_rect(self, size: tuple[int, int]) -> pygame.Rect:
        """The part of a screen of `size` where nothing gets cut by the bezel or the tube."""
        w, h = size
        mx, my = round(w * self.safe_area), round(h * self.safe_area)
        return pygame.Rect(mx, my, w - 2 * mx, h - 2 * my)


def _read(path: Path) -> dict:
    """theme.toml as a dict: empty if there is none; an error if it is broken."""
    if tomllib is None or not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))
