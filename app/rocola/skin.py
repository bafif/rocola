"""The skin: draws every piece of the jukebox with what the theme says.

The scenes ask for a backdrop, a marquee, a title card, a cursor, lamps, a record or a line
of text with a *tone* ("normal", "dim", "alert"…) and never name a color, a font file or an
image. What does not change (the backdrop, the marquee, a card, a line of text) is drawn once
per size and kept, already in the screen's pixel format, so an old PC only redraws what moves.
"""

from __future__ import annotations

import math
from collections import OrderedDict

import pygame

from .theme import Color, Theme, mix

# What a tone paints with: (color role, over the background or over a card).
TONES = {
    "normal": "on_dark",
    "dim": "on_dark_dim",
    "alert": "glow",
    "selected": "background",  # on the cursor bar
    "ink": "text",  # on a card or the marquee
    "ink_dim": "text_dim",
    "code": "accent",
}


def _layer(size: tuple[int, int], alpha: bool = False) -> pygame.Surface:
    """A surface in the screen's own format (16 bpp included), so blitting it costs little."""
    size = (max(1, size[0]), max(1, size[1]))
    screen = pygame.display.get_surface()
    if alpha:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        return surf.convert_alpha() if screen is not None else surf
    return pygame.Surface(size, 0, screen) if screen is not None else pygame.Surface(size)


class _Cache(OrderedDict):
    """A small least-recently-used cache: old entries go when it is full."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = limit

    def get_or(self, key, make):
        if key in self:
            self.move_to_end(key)
            return self[key]
        value = self[key] = make()
        if len(self) > self.limit:
            self.popitem(last=False)
        return value


class Skin:
    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self._layers = _Cache(16)  # backdrops, marquees: one per size and text
        self._texts = _Cache(512)
        self._cards = _Cache(64)

    # --- color ----------------------------------------------------------------
    def tone(self, tone: str) -> Color:
        return self.theme.color(TONES.get(tone, "on_dark"))

    # --- text -----------------------------------------------------------------
    def font(self, role: str, size: int) -> pygame.font.Font:
        return self.theme.font(role, size)

    def line_height(self, size: int, role: str = "body") -> int:
        return self.font(role, size).get_height()

    def shrink_to(self, size: int, height: int, role: str = "body") -> int:
        """`size`, or smaller until a line fits in `height` (never under the display's minimum)."""
        while size > 1 and self.line_height(size, role) > height:
            if self.font(role, size - 1) is self.font(role, size):
                break  # both are already the smallest the display allows
            size -= 1
        return size

    def fit(self, text: str, max_width: int, size: int, role: str = "body") -> str:
        """`text` cut with "…" so it is at most `max_width` pixels wide."""
        font = self.font(role, size)
        if font.size(text)[0] <= max_width:
            return text
        lo, hi = 0, len(text)  # longest prefix that fits, by bisection: few size() calls
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.size(text[:mid].rstrip() + "…")[0] <= max_width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    def render(
        self, text: str, size: int, tone: str = "normal", role: str = "body", max_width: int = 0
    ) -> pygame.Surface:
        """`text` drawn once and kept: the next frame with the same text only blits it."""
        key = (text, size, tone, role, max_width)

        def make() -> pygame.Surface:
            shown = self.fit(text, max_width, size, role) if max_width > 0 else text
            return self.font(role, size).render(shown, self.theme.antialias, self.tone(tone))

        return self._texts.get_or(key, make)

    def text(
        self,
        surface: pygame.Surface,
        text: str,
        pos: tuple[int, int],
        size: int,
        tone: str = "normal",
        role: str = "body",
        max_width: int = 0,
        align: str = "left",
    ) -> pygame.Rect:
        """Draw `text` at `pos` (its left, center or right edge, by `align`); its rect."""
        img = self.render(text, size, tone, role, max_width)
        x, y = pos
        if align == "center":
            x -= img.get_width() // 2
        elif align == "right":
            x -= img.get_width()
        return surface.blit(img, (x, y))

    # --- layers ---------------------------------------------------------------
    def backdrop(self, surface: pygame.Surface) -> None:
        """The cabinet behind everything: the background color and the theme's cabinet."""
        size = surface.get_size()

        def make() -> pygame.Surface:
            layer = _layer(size)
            layer.fill(self.theme.color("background"))
            cabinet = self.theme.piece("cabinet")
            if cabinet is not None:
                layer.blit(cabinet.render(*size), (0, 0))
            return layer

        surface.blit(self._layers.get_or(("backdrop", size), make), (0, 0))

    def panel(self, surface: pygame.Surface) -> None:
        """The operator panel's backdrop: the same theme, sober, with no artwork."""
        surface.fill(self.theme.color("background"))

    def marquee(
        self, surface: pygame.Surface, rect: pygame.Rect, title: str, subtitle: str = ""
    ) -> pygame.Rect:
        """The marquee across the top: the theme's piece, or a band of card paper."""
        rect = pygame.Rect(rect)
        key = ("marquee", rect.size, title, subtitle)

        def make() -> pygame.Surface:
            w, h = rect.size
            layer = _layer((w, h))
            piece = self.theme.piece("marquee")
            if piece is not None:
                layer.fill(self.theme.color("background"))
                layer.blit(piece.render(w, h), (0, 0))
            else:
                layer.fill(self.theme.color("surface"))
                rule = max(2, h // 16)
                layer.fill(self.theme.color("accent"), (0, h - rule, w, rule))
            pad = max(8, w // 50)
            big = max(10, h // 2)
            timg = self.render(title, big, "ink", "marquee", w - 2 * pad)
            if subtitle:
                small = max(10, h // 3)
                simg = self.render(subtitle, small, "ink_dim", "body", w // 2)
                layer.blit(simg, (w - pad - simg.get_width(), (h - simg.get_height()) // 2))
                timg = self.render(title, big, "ink", "marquee", w - 3 * pad - simg.get_width())
            layer.blit(timg, (pad, (h - timg.get_height()) // 2))
            return layer

        return surface.blit(self._layers.get_or(key, make), rect.topleft)

    # --- selection ------------------------------------------------------------
    def cursor_bar(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        """The bar under the selected line of a list (operator panel)."""
        return surface.fill(self.theme.color("glow"), rect)

    def cursor(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        """The light around the selected card: the theme's piece, or a glow outline."""
        rect = pygame.Rect(rect)
        piece = self.theme.piece("cursor")
        if piece is not None:
            return surface.blit(piece.render(*rect.size), rect.topleft)
        width = max(2, rect.height // 16)  # never 1 px: it flickers on an interlaced tube
        return pygame.draw.rect(surface, self.theme.color("glow"), rect, width)

    # --- cards ----------------------------------------------------------------
    def card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        code: str,
        title: str,
        subtitle: str = "",
        selected: bool = False,
    ) -> pygame.Rect:
        """A title card: code at the left, title and a second line (artist, songs…)."""
        rect = pygame.Rect(rect)
        key = (rect.size, code, title, subtitle)
        surface.blit(
            self._cards.get_or(key, lambda: self._card(rect.size, code, title, subtitle)),
            rect.topleft,
        )
        if selected:
            self.cursor(surface, rect.inflate(4, 4))
        return rect.inflate(4, 4)

    def _card(self, size: tuple[int, int], code: str, title: str, subtitle: str):
        w, h = size
        layer = _layer(size)
        layer.fill(self.theme.color("background"))
        strip = self.theme.piece("strip")
        if strip is not None:
            layer.blit(strip.render(w, h), (0, 0))
        else:
            layer.fill(self.theme.color("surface"))
            band = max(2, h // 10)  # the stripe across the paper
            layer.fill(self.theme.color("accent"), (0, h // 2 - band // 2, w, band))
        pad = max(3, h // 10)
        code_size = max(10, h * 2 // 5)
        cimg = self.render(code, code_size, "code", "digits")
        layer.blit(cimg, (pad, (h - cimg.get_height()) // 2))
        x = pad * 2 + max(cimg.get_width(), self.font("digits", code_size).size("M00")[0])
        text_w = w - x - pad
        line = max(10, h * 3 // 10)
        if subtitle:
            top = self.render(title, line, "ink", "strip", text_w)
            bottom = self.render(subtitle, max(10, h // 4), "ink_dim", "body", text_w)
            layer.blit(top, (x, h // 2 - top.get_height()))
            layer.blit(bottom, (x, h // 2 + 1))
        else:
            top = self.render(title, line, "ink", "strip", text_w)
            layer.blit(top, (x, (h - top.get_height()) // 2))
        return layer

    # --- lamps and record -----------------------------------------------------
    def lamps(self, surface: pygame.Surface, rect: pygame.Rect, lit: list[bool]) -> pygame.Rect:
        """A row of lamps across `rect`, lit or not (progress, chasers, the volume)."""
        rect = pygame.Rect(rect)
        if not lit:
            return rect
        on, off = self.theme.piece("lamp_on"), self.theme.piece("lamp_off")
        step = rect.width / len(lit)
        radius = max(2, min(int(step) // 2 - 1, rect.height // 2))
        dim = mix(self.theme.color("glow"), self.theme.color("background"), 0.25)
        for i, state in enumerate(lit):
            cx = rect.x + int(step * i + step / 2)
            piece = on if state else off
            if piece is not None:
                img = piece.render(radius * 2, radius * 2)
                surface.blit(img, (cx - radius, rect.centery - radius))
            else:
                color = self.theme.color("glow") if state else dim
                pygame.draw.circle(surface, color, (cx, rect.centery), radius)
        return rect

    def record(self, diameter: int, label: pygame.Surface | None) -> Record:
        return Record(self, diameter, label)


class Record:
    """A 45 spinning, with the cover as its label.

    The label is rotated FRAMES times when the song starts; spinning is only picking which one
    to blit, by the clock (so it turns at 45 rpm on a 50 Hz and on a 60 Hz screen). The grooves
    are symmetric and the shine stays put: neither is rotated.
    """

    FRAMES = 40  # 9° each: 45 rpm at 30 frames a second

    def __init__(self, skin: Skin, diameter: int, label: pygame.Surface | None) -> None:
        self.diameter = d = max(16, diameter)
        theme = skin.theme
        vinyl = mix(theme.color("background"), (0, 0, 0), 0.35)
        groove = mix(theme.color("on_dark"), vinyl, 0.12)
        self.base = _layer((d, d), alpha=True)
        self.base.fill((0, 0, 0, 0))
        c = d // 2
        pygame.draw.circle(self.base, vinyl, (c, c), c)
        label_r = int(d * 0.19)
        for r in range(label_r + 4, c - 2, max(3, d // 60)):
            pygame.draw.circle(self.base, groove, (c, c), r, 1)
        self.label_d = label_d = label_r * 2
        face = _layer((label_d, label_d), alpha=True)
        face.fill((0, 0, 0, 0))
        pygame.draw.circle(face, theme.color("accent"), (label_r, label_r), label_r)
        if label is not None:
            art = pygame.transform.smoothscale(label.convert_alpha(), (label_d, label_d))
            mask = _layer((label_d, label_d), alpha=True)
            mask.fill((0, 0, 0, 0))
            pygame.draw.circle(mask, (255, 255, 255, 255), (label_r, label_r), label_r)
            art.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            face.blit(art, (0, 0))
        hole = max(2, d // 40)
        pygame.draw.circle(face, vinyl, (label_r, label_r), hole)
        self.frames = [pygame.transform.rotate(face, -9 * i) for i in range(self.FRAMES)]
        self.shine = _layer((d, d), alpha=True)
        self.shine.fill((0, 0, 0, 0))
        light = (*theme.color("on_dark"), 28)
        pygame.draw.polygon(self.shine, light, [(c, c), (d, int(d * 0.2)), (d, int(d * 0.45))])
        pygame.draw.polygon(self.shine, light, [(c, c), (0, int(d * 0.55)), (0, int(d * 0.8))])

    def index(self, seconds: float, rpm: float = 45.0) -> int:
        """Which rotated label shows `seconds` after the record started."""
        return int(seconds * rpm / 60 * self.FRAMES) % self.FRAMES

    def draw(self, surface: pygame.Surface, center: tuple[int, int], frame: int) -> pygame.Rect:
        rect = self.base.get_rect(center=center)
        surface.blit(self.base, rect)
        label = self.frames[frame % self.FRAMES]
        surface.blit(label, label.get_rect(center=center))
        surface.blit(self.shine, rect)
        return rect


def ring(n: int, start: int, length: int) -> list[bool]:
    """`length` lamps lit in a row of `n`, starting at `start` and wrapping: a chaser."""
    return [((i - start) % n) < length for i in range(n)]


def progress(n: int, fraction: float) -> list[bool]:
    """The first lamps of `n` lit, as many as `fraction` (0 to 1) of the row."""
    lit = math.floor(max(0.0, min(1.0, fraction)) * n + 1e-9)
    return [i < lit for i in range(n)]
