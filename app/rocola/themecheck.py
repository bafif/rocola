"""Check a theme before it reaches a jukebox: `python -m rocola.theme check <theme>…`.

For every kind of display it loads the theme with that variant and looks at what the jukebox
cannot fix on its own: text that does not stand out from what is behind it (the minimum of
that display; on a TV, by luminance), fonts without the Spanish letters, and files the theme
names that are missing or do not load. With no problems it exits 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from .config import ASSETS_DIR, DISPLAYS
from .theme import FONT_ROLES, Color, Theme, _read

# Letters every font has to draw: a title in Spanish uses all of them.
SAMPLE = "ÁÉÍÓÚÜÑ¿¡áéíóúüñ"
# The digits font only draws the codes of the cards (a page letter, never I or O, and the place
# in it) and the numbers of the buttons: a seven-segment font is enough.
SAMPLES = {"digits": "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"}
# A character no font has: what a font draws for it is what it draws for any letter it lacks.
_ABSENT = "\U0010fffd"

# Text and what is behind it, by role: the pairs every screen uses.
PAIRS = (
    ("text", "surface"),
    ("text_dim", "surface"),
    ("accent", "surface"),
    ("on_dark", "background"),
    ("on_dark_dim", "background"),
    ("glow", "background"),
)


def _linear(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: Color) -> float:
    """WCAG relative luminance, 0 (black) to 1 (white)."""
    r, g, b = (_linear(c) for c in color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: Color, b: Color) -> float:
    """WCAG contrast ratio, 1 to 21."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def luma(color: Color) -> float:
    """What a composite TV keeps of a color (Rec. 601 luma), 0 to 1."""
    r, g, b = color
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def check(theme_dir: Path, displays: tuple[str, ...] = DISPLAYS) -> list[str]:
    """Every problem of the theme in `theme_dir`, one line each; empty when it is fine."""
    if not (theme_dir / "theme.toml").is_file():
        return [f"{theme_dir}: no theme.toml"]
    try:
        _read(theme_dir / "theme.toml")
    except Exception as exc:  # noqa: BLE001 — anything that makes the jukebox ignore it
        return [f"theme.toml: {exc}"]
    problems: list[str] = []
    for display in displays:
        theme = Theme.load(theme_dir, display)
        profile = theme.profile
        for fg, bg in PAIRS:
            a, b = theme.color(fg), theme.color(bg)
            ratio = contrast(a, b)
            if ratio < profile.min_contrast:
                problems.append(
                    f"{display}: {fg} on {bg}: {ratio:.1f}:1, needs {profile.min_contrast}:1"
                )
            gap = abs(luma(a) - luma(b))
            if gap < profile.min_luma_gap:
                problems.append(
                    f"{display}: {fg} on {bg}: luma {gap:.2f} apart, needs {profile.min_luma_gap}"
                )
        problems += [f"{display}: missing file {name}" for name in theme.missing]
        for role in FONT_ROLES:
            absent = lacking(theme.font(role, 24), SAMPLES.get(role, SAMPLE))
            if absent:
                problems.append(f"{display}: font {role} has no {absent}")
        for name in theme._pieces:
            if theme.piece(name) is None:
                problems.append(f"{display}: piece {name} does not load")
    return list(dict.fromkeys(problems))  # the same problem on every display, once


def lacking(font: pygame.font.Font, text: str) -> str:
    """The characters of `text` that `font` has no glyph for.

    SDL never says a glyph is missing (its metrics are those of the empty box the font draws
    instead), so each letter is drawn and compared with a character no font has.
    """
    blank = _drawn(font, _ABSENT)
    return "".join(ch for ch in text if _drawn(font, ch) == blank)


def _drawn(font: pygame.font.Font, ch: str) -> tuple[tuple[int, int], bytes]:
    img = font.render(ch, False, (255, 255, 255), (0, 0, 0))
    return img.get_size(), pygame.image.tobytes(img, "RGB")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "check":
        print("usage: python -m rocola.theme check <theme>… | --all", file=sys.stderr)
        return 2
    themes = ASSETS_DIR / "themes"
    names = (
        sorted(p.parent.name for p in themes.glob("*/theme.toml"))
        if argv[1:] == ["--all"]
        else argv[1:]
    )
    pygame.font.init()
    failed = 0
    for name in names:
        folder = Path(name) if "/" in name else themes / name
        problems = check(folder)
        print(f"{folder.name}: {'ok' if not problems else f'{len(problems)} problem(s)'}")
        for line in problems:
            print(f"  {line}")
        failed += bool(problems)
    return 1 if failed else 0
