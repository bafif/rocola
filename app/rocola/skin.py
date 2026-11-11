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


def _int(value: object, default: int, low: int, high: int) -> int:
    """A whole number from the theme, kept between `low` and `high`; `default` if it is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        return default
    return max(low, min(high, value))


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

    # --- what the display asks for --------------------------------------------
    def safe_rect(self, surface: pygame.Surface) -> pygame.Rect:
        """Where nothing gets cut by the bezel or the tube (the display's margin)."""
        return self.theme.safe_rect(surface.get_size())

    def grid(self) -> tuple[int, int]:
        """Cards a page, as (columns, rows): 10 on an LCD, 8 on a PC tube, 6 at 15 kHz and TV."""
        return self.theme.profile.cards

    def chaser(self) -> tuple[int, int]:
        """The marquee's lamps: how many, and how long each step of the chase lasts in ms."""
        spec = self.theme.effect("chaser")
        spec = spec if isinstance(spec, dict) else {}
        return _int(spec.get("lamps"), 16, 4, 64), _int(spec.get("step_ms"), 120, 40, 1000)

    def bubbles(self) -> tuple[int, int]:
        """The bubble tubes at the sides: how many (0 or 2, one a side) and bubbles in each."""
        spec = self.theme.effect("bubbles")
        spec = spec if isinstance(spec, dict) else {}
        tubes = _int(spec.get("tubes"), 0, 0, 2)
        return (2 if tubes else 0), _int(spec.get("per_tube"), 5, 1, 12)

    def rpm(self) -> float:
        """How fast the record on the now playing screen turns (45 unless the theme says)."""
        spec = self.theme.effect("record")
        value = spec.get("rpm") if isinstance(spec, dict) else None
        ok = isinstance(value, (int, float)) and not isinstance(value, bool) and 16 <= value <= 78
        return float(value) if ok else 45.0

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
    def _backdrop(self, size: tuple[int, int]) -> pygame.Surface:
        def make() -> pygame.Surface:
            layer = _layer(size)
            layer.fill(self.theme.color("background"))
            cabinet = self.theme.piece("cabinet")
            if cabinet is not None:
                layer.blit(cabinet.render(*size), (0, 0))
            return layer

        return self._layers.get_or(("backdrop", size), make)

    def backdrop(self, surface: pygame.Surface) -> None:
        """The cabinet behind everything: the background color and the theme's cabinet."""
        surface.blit(self._backdrop(surface.get_size()), (0, 0))

    def restore(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        """Put the cabinet back under `rect`, before drawing again what moves there."""
        rect = pygame.Rect(rect).clip(surface.get_rect())
        surface.blit(self._backdrop(surface.get_size()), rect.topleft, rect)
        return rect

    def shade(self, surface: pygame.Surface, rect: pygame.Rect, amount: float) -> pygame.Rect:
        """Darken `rect` by `amount`, from 0 (as it is) to 1 (black): a light not yet on."""
        rect = pygame.Rect(rect)
        if amount > 0:
            shadow = self._layers.get_or(("shade", rect.size), lambda: _layer(rect.size))
            shadow.fill((0, 0, 0))
            shadow.set_alpha(round(255 * min(1.0, amount)))
            surface.blit(shadow, rect.topleft)
        return rect

    def panel(self, surface: pygame.Surface) -> None:
        """The operator panel's backdrop: the same theme, sober, with no artwork."""
        surface.fill(self.theme.color("background"))

    def panel_header(
        self, surface: pygame.Surface, rect: pygame.Rect, title: str, subtitle: str = ""
    ) -> pygame.Rect:
        """The operator panel's header: the title in the text font, the jukebox's name at the
        right and a rule underneath; no artwork and no effects."""
        rect = pygame.Rect(rect)
        rule = max(2, rect.h // 16)  # never 1 px: it flickers on an interlaced tube
        size = self.shrink_to(max(14, rect.h * 3 // 5), rect.h - rule - 2)
        y = rect.y + (rect.h - rule - self.line_height(size)) // 2
        right = rect.right
        if subtitle:
            sub = self.text(
                surface, subtitle, (right, y), size, "dim", max_width=rect.w // 3, align="right"
            )
            right = sub.x - max(8, rect.h // 3)
        self.text(surface, title, (rect.x, y), size, "alert", max_width=right - rect.x)
        surface.fill(self.tone("dim"), (rect.x, rect.bottom - rule, rect.w, rule))
        return rect

    def legend(
        self, surface: pygame.Surface, rect: pygame.Rect, items: list[tuple[str, str, str]]
    ) -> pygame.Rect:
        """What each button does here, drawn as the cabinet's controls: `items` are
        (control, what its cap says, what it does), the control "stick_v" or "stick_h" (the
        stick, up and down or left and right) or "button". From the left; what does not fit
        is left out. The rect it took."""
        rect = pygame.Rect(rect)
        cap = max(8, rect.h - 2)
        size = self.shrink_to(max(10, rect.h * 3 // 5), rect.h)
        gap = max(4, cap // 3)
        x = rect.x
        for control, label, text in items:
            img = self.render(text, size, "dim")
            width = cap + gap // 2 + img.get_width()
            if x + width > rect.right:
                break
            self._control(
                surface, pygame.Rect(x, rect.centery - cap // 2, cap, cap), control, label
            )
            surface.blit(img, (x + cap + gap // 2, rect.centery - img.get_height() // 2))
            x += width + gap * 2
        return pygame.Rect(rect.x, rect.y, max(0, x - gap * 2 - rect.x), rect.h)

    def _control(self, surface, box: pygame.Rect, control: str, label: str) -> None:
        glow, accent = self.theme.color("glow"), self.theme.color("accent")
        r = box.w // 2
        if control == "button":  # a round cap with a ring of light, and its number
            pygame.draw.circle(surface, accent, box.center, r)
            pygame.draw.circle(surface, glow, box.center, r, max(2, r // 4))
            if label:
                size = self.shrink_to(max(8, box.h * 3 // 5), box.h - 2 * max(2, r // 4), "digits")
                img = self.render(label, size, "normal", "digits")
                surface.blit(img, img.get_rect(center=box.center))
            return
        # The stick: a ball and two arrows, up and down or left and right.
        cx, cy = box.center
        pygame.draw.circle(surface, glow, box.center, max(2, r // 3))
        a = max(2, r // 2)
        if control == "stick_v":
            arrows = [
                [(cx, box.y), (cx - a, box.y + a), (cx + a, box.y + a)],
                [(cx, box.bottom - 1), (cx - a, box.bottom - 1 - a), (cx + a, box.bottom - 1 - a)],
            ]
        else:
            arrows = [
                [(box.x, cy), (box.x + a, cy - a), (box.x + a, cy + a)],
                [(box.right - 1, cy), (box.right - 1 - a, cy - a), (box.right - 1 - a, cy + a)],
            ]
        for arrow in arrows:
            pygame.draw.polygon(surface, glow, arrow)

    def marquee(
        self, surface: pygame.Surface, rect: pygame.Rect, title: str, subtitle: str = ""
    ) -> pygame.Rect:
        """The marquee across the top: the theme's piece, or a band of card paper."""
        rect = pygame.Rect(rect)
        screen = surface.get_size()
        key = ("marquee", screen, tuple(rect), title, subtitle)

        def make() -> pygame.Surface:
            w, h = rect.size
            layer = _layer((w, h))
            piece = self.theme.piece("marquee")
            pad = max(8, w // 50)
            if piece is not None:  # over the bit of cabinet behind it, for its round corners
                layer.blit(self._backdrop(screen), (0, 0), rect)
                layer.blit(piece.render(w, h), (0, 0))
                cuts = piece.slice or (0, 0, 0, 0)  # the text keeps off the rim at the sides
                left, right = max(pad, cuts[0]), max(pad, cuts[2])
            else:
                layer.fill(self.theme.color("surface"))
                rule = max(2, h // 16)
                layer.fill(self.theme.color("accent"), (0, h - rule, w, rule))
                left = right = pad
            room = w - left - right
            big = max(10, h // 2)
            timg = self.render(title, big, "ink", "marquee", room)
            if subtitle:
                small = max(10, h // 3)
                simg = self.render(subtitle, small, "ink_dim", "body", room // 2)
                layer.blit(simg, (w - right - simg.get_width(), (h - simg.get_height()) // 2))
                timg = self.render(title, big, "ink", "marquee", room - pad - simg.get_width())
            layer.blit(timg, (left, (h - timg.get_height()) // 2))
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
        kind: str = "strip",
    ) -> pygame.Rect:
        """A card: code at the left, title and a second line (artist, songs…).

        `kind` is "strip" for a song (a title strip, with its stripe across the paper) or
        "index" for an artist or an album (an index card, framed)."""
        rect = pygame.Rect(rect)
        key = (rect.size, code, title, subtitle, kind)
        surface.blit(
            self._cards.get_or(key, lambda: self._card(rect.size, code, title, subtitle, kind)),
            rect.topleft,
        )
        if selected:
            self.cursor(surface, rect.inflate(4, 4))
        return rect.inflate(4, 4)

    def _card(self, size: tuple[int, int], code: str, title: str, subtitle: str, kind: str):
        w, h = size
        layer = _layer(size)
        layer.fill(self.theme.color("background"))
        piece = self.theme.piece(kind)
        # An index card without its own piece: the strip's paper (or the surface) in a frame.
        frame = max(2, h // 20) if kind == "index" and piece is None else 0
        piece = piece or self.theme.piece("strip")
        if piece is not None:
            layer.blit(piece.render(w, h), (0, 0))
        else:
            layer.fill(self.theme.color("surface"))
        if frame:
            pygame.draw.rect(layer, self.theme.color("accent"), layer.get_rect(), frame)
        pad = max(3, h // 10) + frame
        # With a piece, the text keeps off its edges (its nine-slice cuts at the sides).
        cuts = piece.slice if piece is not None and piece.slice else (0, 0, 0, 0)
        left, right = max(pad, cuts[0]), max(pad, cuts[2])
        inner = h - 2 * pad  # the letters shrink to fit (down to the display's minimum)
        code_size = self.shrink_to(max(10, h * 2 // 5), inner, "digits")
        while self.font("digits", code_size).size("M00")[0] > w // 4:  # a narrow card: the
            if self.font("digits", code_size - 1) is self.font("digits", code_size):
                break  # title needs the room more (never under the display's minimum)
            code_size -= 1
        cimg = self.render(code, code_size, "code", "digits")
        layer.blit(cimg, (left, (h - cimg.get_height()) // 2))
        x = left + pad + max(cimg.get_width(), self.font("digits", code_size).size("M00")[0])
        text_w = w - x - right
        band = max(2, h // 10)
        if kind == "strip":  # a title strip: the stripe across, clear of the code
            start = x - pad // 2
            layer.fill(
                self.theme.color("accent"),
                (start, h // 2 - band // 2, w - right // 2 - start, band),
            )
        line = max(10, h * 3 // 10)
        while self.font("strip", line).size("abcdefghijklmn")[0] > text_w:  # ~14 letters fit
            if self.font("strip", line - 1) is self.font("strip", line):
                break  # never under the display's minimum
            line -= 1
        if subtitle:
            line = self.shrink_to(line, inner * 11 // 20, "strip")
            small = self.shrink_to(max(10, h // 4), inner - self.line_height(line, "strip"))
            small = min(small, line)  # the second line never bigger than the title
            top = self.render(title, line, "ink", "strip", text_w)
            bottom = self.render(subtitle, small, "ink_dim", "body", text_w)
            gap = band // 2 + 1 if kind == "strip" else 1  # above and below the stripe
            layer.blit(top, (x, h // 2 - gap - top.get_height()))
            layer.blit(bottom, (x, h // 2 + gap))
        else:
            top = self.render(title, self.shrink_to(line, inner, "strip"), "ink", "strip", text_w)
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

    def tube(
        self, surface: pygame.Surface, rect: pygame.Rect, bubbles: list[tuple[float, float]]
    ) -> pygame.Rect:
        """A bubble tube over the cabinet, with `bubbles` at (across, up) as fractions of it."""
        rect = pygame.Rect(rect)
        surface.blit(self._backdrop(surface.get_size()), rect.topleft, rect)
        piece = self.theme.piece("tube")
        cap = 0
        if piece is not None:
            surface.blit(piece.render(*rect.size), rect.topleft)
            cap = (piece.slice[1] if piece.slice else rect.w // 2) + 1
        else:  # in colors: the liquid in a rim of light
            liquid = mix(self.theme.color("glow"), self.theme.color("background"), 0.45)
            radius = rect.w // 2
            pygame.draw.rect(surface, liquid, rect, border_radius=radius)
            pygame.draw.rect(surface, self.theme.color("glow"), rect, 2, border_radius=radius)
            cap = radius
        size = max(2, rect.w // 5)
        inside = rect.inflate(-2 * size, -2 * (cap + size))
        color = self.theme.color("on_dark")
        for across, up in bubbles:
            x = inside.x + round(across * inside.w)
            y = inside.bottom - round(up * inside.h)
            pygame.draw.circle(surface, color, (x, y), size, max(1, size // 2))
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
        disc = _layer((d, d), alpha=True)  # the shine stays on the vinyl
        disc.fill((0, 0, 0, 0))
        pygame.draw.circle(disc, (255, 255, 255, 255), (c, c), c)
        self.shine.blit(disc, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

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


def chase(n: int, step: int, every: int = 3) -> list[bool]:
    """One lamp in every `every` lit, the pattern moved `step` places along: lights that run."""
    return [(i - step) % every == 0 for i in range(n)]


def ring(n: int, start: int, length: int) -> list[bool]:
    """`length` lamps lit in a row of `n`, starting at `start` and wrapping: a chaser."""
    return [((i - start) % n) < length for i in range(n)]


def progress(n: int, fraction: float) -> list[bool]:
    """The first lamps of `n` lit, as many as `fraction` (0 to 1) of the row."""
    lit = math.floor(max(0.0, min(1.0, fraction)) * n + 1e-9)
    return [i < lit for i in range(n)]
