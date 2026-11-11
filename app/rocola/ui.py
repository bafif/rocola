"""Escenas de la UI: biblioteca, now-playing, menú y las pantallas del operador.

Cada escena maneja acciones (ver input.py) y se dibuja con skin.py: dice qué va
(una tarjeta, una línea de texto «dim», el cursor) y el tema decide cómo se ve.
Ninguna escena nombra un color, una fuente ni una imagen.
"""

from __future__ import annotations

import io
import threading
import time

import pygame

from . import audio, bt, i18n, library, sysinfo
from . import input as actions
from .i18n import t
from .skin import chase, progress


class Scene:
    # True while something on it moves: the app then draws every frame instead of resting.
    animating = False

    def __init__(self, app):
        self.app = app

    @property
    def skin(self):
        return self.app.skin

    def on_enter(self) -> None: ...

    def handle(self, action: str) -> None: ...

    def draw(self, surface) -> list | None:
        """Draw the scene; the rects that changed, or None when the whole screen did."""

    def _hint(self, surface, text: str) -> None:
        """The line at the bottom that says what each button does here."""
        w, h = surface.get_size()
        size = max(13, h // 26)
        y = h - self.skin.line_height(size) - 6
        self.skin.text(surface, text, (16, y), size, "dim", max_width=w - 32)


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] if path else t("library.unknown_song")


class JukeboxScene(Scene):
    """A screen of the jukebox itself (the selector, now playing), not of the operator panel:
    the cabinet, and on top the marquee with a row of lamps that run for a moment when a song
    starts. Everything sits inside the display's safe area."""

    # How long the lamps run when a song starts, by effects level (effects.py).
    CHASE_S = {"completo": 4.0, "suave": 2.0, "apagado": 0.0}

    def _layout(self, surface) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Where the marquee, its lamps and the rest of the screen go."""
        h = surface.get_height()
        safe = self.skin.safe_rect(surface)
        total = max(40, h // 7)
        lamps_h = max(8, total // 5)
        marquee = pygame.Rect(safe.x, safe.y, safe.w, total - lamps_h)
        lamps = pygame.Rect(safe.x, marquee.bottom, safe.w, lamps_h)
        top = lamps.bottom + max(4, h // 60)
        return marquee, lamps, pygame.Rect(safe.x, top, safe.w, safe.bottom - top)

    def _chase_step(self) -> int | None:
        """The step the running lamps are on, or None when they rest (all lit)."""
        started = self.app.song_started
        if started is None:
            return None
        elapsed = time.monotonic() - started
        if not 0 <= elapsed < self.CHASE_S.get(self.app.effects.level, 0.0):
            return None
        return int(elapsed * 1000) // self.skin.chaser()[1]

    @property
    def animating(self) -> bool:
        return self._chase_step() is not None

    def _lamps(self) -> list[bool]:
        count = self.skin.chaser()[0]
        step = self._chase_step()
        return [True] * count if step is None else chase(count, step)

    def _frame(self, surface, subtitle: str) -> pygame.Rect:
        """The cabinet, the marquee and its lamps; the rect left for the scene."""
        marquee, lamps, rest = self._layout(surface)
        self.skin.backdrop(surface)
        self.skin.marquee(surface, marquee, self.app.marquee_title(), subtitle)
        self.skin.lamps(surface, lamps, self._lamps())
        return rest

    def _motion(self, surface) -> list:
        """A frame where only the lamps moved: they alone are drawn and sent to the screen."""
        lamps = self._layout(surface)[1]
        self.skin.restore(surface, lamps)
        return [self.skin.lamps(surface, lamps, self._lamps())]


class LibraryScene(JukeboxScene):
    """The selector: the library by artist and album (library.py builds the views) as cards
    in two columns, a page at a time, each with its code (A1, A2…). ↑↓ move one card, ←→ a
    whole page; selecting a song plays it. Back goes up one level, and from the top to the
    now playing screen."""

    def __init__(self, app):
        super().__init__(app)
        self.songs: list[dict] = []
        self.stack: list[library.View] = [library.View("", [])]
        self.error: str | None = None

    @property
    def view(self) -> library.View:
        return self.stack[-1]

    def on_enter(self) -> None:
        # Only when nothing is loaded yet (or the last load failed). Reloads come from
        # the app, on (re)connecting and when MPD's db_update changes; re-reading the
        # whole listallinfo on every visit would freeze old hardware for a moment.
        if not self.songs or self.error:
            self.refresh()

    def refresh(self) -> None:
        self.error = None
        try:
            self.songs = self.app.mpd.all_files()
        except Exception as exc:  # noqa: BLE001 - mostrar cualquier fallo en pantalla
            self.songs = []
            self.error = str(exc)
            return  # keep the place: the next refresh reopens it
        self.stack = library.reopen(self.songs, self.stack)

    def relabel(self) -> None:
        """Rebuild the views from the songs already loaded (after a language switch)."""
        if self.songs:
            self.stack = library.reopen(self.songs, self.stack)

    def handle(self, action: str) -> None:
        view = self.view
        count = len(view.rows)
        if action in (actions.UP, actions.DOWN, actions.LEFT, actions.RIGHT) and count:
            if action == actions.UP:
                view.index = (view.index - 1) % count
            elif action == actions.DOWN:
                view.index = (view.index + 1) % count
            else:
                delta = -1 if action == actions.LEFT else 1
                view.index = library.flip_page(view.index, count, self._per_page(), delta)
        elif action == actions.SELECT and count:
            self._select(view.rows[view.index])
        elif action == actions.PLAYPAUSE:
            self.app.mpd_safe(lambda c: c.toggle())
        elif action == actions.NEXT:
            self.app.mpd_safe(lambda c: c.next())
        elif action == actions.PREV:
            self.app.mpd_safe(lambda c: c.previous())
        elif action == actions.VOLUP:
            self.app.mpd_safe(lambda c: c.change_volume(+5))
        elif action == actions.VOLDOWN:
            self.app.mpd_safe(lambda c: c.change_volume(-5))
        elif action == actions.BACK:
            if len(self.stack) > 1:
                self.stack.pop()
            else:
                self.app.set_scene("nowplaying")
        elif action == actions.MENU:
            self.app.open_menu()

    def _select(self, row: library.Row) -> None:
        if row.is_folder:
            self.stack.append(library.open_row(row))
            return
        uri = (row.song or {}).get("file")
        if uri:
            self.app.mpd_safe(lambda c: c.play_uri(uri))
            self.app.set_scene("nowplaying")

    def _per_page(self) -> int:
        columns, rows = self.skin.grid()
        return columns * rows

    def draw(self, surface) -> list | None:
        if self.app.motion_only:
            return self._motion(surface)
        h = surface.get_height()
        skin = self.skin
        # The marquee says where in the library we are.
        where = " / ".join(v.title for v in self.stack[1:]) or t("header.library")
        area = self._frame(surface, where)

        if self.error or not self.songs:
            size = max(16, h // 18)
            if self.error:
                text, tone = t("library.mpd_error", error=self.error), "alert"
            else:
                text, tone = t("library.empty"), "dim"
            skin.text(surface, text, area.topleft, size, tone, max_width=area.w)
            return None

        view = self.view
        columns, rows = skin.grid()
        per_page = columns * rows
        small = max(13, h // 26)
        foot_h = skin.line_height(small) + 4
        gap = max(4, h // 60)
        card_w = (area.w - gap * (columns - 1)) // columns
        card_h = (area.h - foot_h - gap * (rows - 1)) // rows

        page = view.index // per_page
        view.top = page * per_page
        for i in range(view.top, min(view.top + per_page, len(view.rows))):
            column, place = divmod(i - view.top, rows)  # down the left column, then the right
            rect = pygame.Rect(
                area.x + column * (card_w + gap), area.y + place * (card_h + gap), card_w, card_h
            )
            row = view.rows[i]
            title, subtitle = library.card_text(row)
            kind = "index" if row.is_folder else "strip"
            code = library.code(i, per_page)
            skin.card(surface, rect, code, title, subtitle, i == view.index, kind)

        pages = -(-len(view.rows) // per_page)
        if pages > 1:
            text = t("library.page", page=page + 1, pages=pages)
            pos = (area.right, area.bottom - foot_h + 2)
            skin.text(surface, text, pos, small, "dim", align="right")
        return None


def _load_cover(data: bytes, side: int):
    """Decode a cover and crop it to a `side` x `side` square (the record's label); None if
    it cannot be read."""
    try:
        img = pygame.image.load(io.BytesIO(data))
        if pygame.display.get_surface() is not None:
            img = img.convert()  # display format: faster blits on old hardware
    except (pygame.error, ValueError, OSError):
        return None
    iw, ih = img.get_size()
    if not iw or not ih:
        return None
    crop = min(iw, ih)  # the middle of a cover that is not square
    img = img.subsurface(((iw - crop) // 2, (ih - crop) // 2, crop, crop))
    try:
        return pygame.transform.smoothscale(img, (side, side))
    except ValueError:  # smoothscale only takes 24/32-bit surfaces
        return pygame.transform.scale(img, (side, side))


def _clock(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _seconds(status: dict) -> tuple[float, float]:
    """How far the song has gone and how long it is, in seconds (0 when MPD does not say)."""
    old = (status.get("time") or "").split(":")  # "elapsed:duration", from MPDs before 0.20
    values = []
    for key, i in (("elapsed", 0), ("duration", 1)):
        value = status.get(key) or (old[i] if len(old) == 2 else "")
        try:
            values.append(max(0.0, float(value)))
        except ValueError:
            values.append(0.0)
    return values[0], values[1]


class NowPlayingScene(JukeboxScene):
    """What is playing: a 45 that turns with the cover as its label (still when paused or with
    the effects off), the title, the artist and the album, lamps for how far the song has gone
    and for the volume, and the song that comes next."""

    def __init__(self, app):
        super().__init__(app)
        self._cover_src: bytes | None = None  # the bytes the record's label came from
        self._cover_img = None
        self._record = None
        self._record_d = 0
        self._record_rect: pygame.Rect | None = None
        self._turned = 0.0  # seconds the record turned before it last stopped
        self._turning_since: float | None = None

    def handle(self, action: str) -> None:
        if action in (actions.BACK, actions.SELECT):
            self.app.set_scene("library")
        elif action == actions.PLAYPAUSE:
            self.app.mpd_safe(lambda c: c.toggle())
        elif action == actions.NEXT:
            self.app.mpd_safe(lambda c: c.next())
        elif action == actions.PREV:
            self.app.mpd_safe(lambda c: c.previous())
        elif action == actions.VOLUP:
            self.app.mpd_safe(lambda c: c.change_volume(+5))
        elif action == actions.VOLDOWN:
            self.app.mpd_safe(lambda c: c.change_volume(-5))
        elif action == actions.MENU:
            self.app.open_menu()

    def _turning(self) -> bool:
        playing = self.app.state.get("status", {}).get("state") == "play"
        return playing and self.app.effects.level != "apagado"

    @property
    def animating(self) -> bool:
        return self._turning() or super().animating

    def _angle(self) -> int:
        """Which of the record's rotated labels shows now: by the clock, not by the frame, so it
        turns at its speed at 50 and at 60 Hz, and stays where it was while paused."""
        now = time.monotonic()
        if self._turning():
            if self._turning_since is None:
                self._turning_since = now
            seconds = self._turned + now - self._turning_since
        else:
            if self._turning_since is not None:
                self._turned += now - self._turning_since
                self._turning_since = None
            seconds = self._turned
        return self._record.index(seconds, self.skin.rpm())

    def _record_for(self, diameter: int):
        """The record with this song's cover as its label, built once per song and size."""
        data = self.app.state.get("cover") if self.app.state.get("song") else None
        if self._record is None or data is not self._cover_src or diameter != self._record_d:
            self._cover_src, self._record_d = data, diameter
            label_d = int(diameter * 0.19) * 2  # what Record makes of it
            self._cover_img = _load_cover(data, max(1, label_d)) if data else None
            self._record = self.skin.record(diameter, self._cover_img)
        return self._record

    def _motion(self, surface) -> list:
        rects = super()._motion(surface)
        if self._turning() and self._record is not None and self._record_rect is not None:
            self.skin.restore(surface, self._record_rect)
            rects.append(self._record.draw(surface, self._record_rect.center, self._angle()))
        return rects

    def draw(self, surface) -> list | None:
        if self.app.motion_only:
            return self._motion(surface)
        h = surface.get_height()
        area = self._frame(surface, t("header.nowplaying"))
        gap = max(8, h // 40)
        diameter = min(area.h, area.w * 2 // 5)
        record = self._record_for(diameter)
        center = (area.x + diameter // 2, area.centery)
        self._record_rect = record.draw(surface, center, self._angle())
        x = area.x + diameter + gap
        self._details(surface, pygame.Rect(x, area.y, area.right - x, area.h))
        return None

    def _details(self, surface, box: pygame.Rect) -> None:
        """Title, artist, album, the lamps and what comes next, centered in `box`; what does
        not fit leaves out the album first and then what comes next."""
        skin = self.skin
        h = surface.get_height()
        song = self.app.state.get("song", {})
        status = self.app.state.get("status", {})
        upcoming = self.app.state.get("next") or {}
        big, body = max(22, h // 12), max(16, h // 20)
        line = skin.line_height(body)
        gap = max(3, h // 80)
        title = song.get("Title") or (_basename(song["file"]) if song.get("file") else "—")
        state = status.get("state", "stop")
        volume = status.get("volume", "")

        # (what, height, how important: 0 always, then the order to leave them out)
        rows = [("title", skin.line_height(big, "marquee"), 0)]
        rows += [("artist", line, 0)] if song.get("Artist") else []
        rows += [("album", line, 2)] if song.get("Album") else []
        rows += [("progress", line, 0)] if song.get("file") else []
        rows += [("volume", line, 0)] if volume.isdigit() else []  # MPD says -1 with no mixer
        rows += [("state", line, 0)] if state != "play" else []
        rows += [("next", line, 1)] if upcoming.get("file") else []
        for level in (2, 1):
            if sum(r[1] + gap for r in rows) - gap <= box.h:
                break
            rows = [r for r in rows if r[2] != level]

        y = box.y + max(0, (box.h - (sum(r[1] + gap for r in rows) - gap)) // 2)
        for what, height, _level in rows:
            if what == "title":
                skin.text(surface, title, (box.x, y), big, "normal", "marquee", box.w)
            elif what in ("artist", "album"):
                text = song.get("Artist" if what == "artist" else "Album", "")
                skin.text(surface, text, (box.x, y), body, "dim", max_width=box.w)
            elif what == "progress":
                elapsed, duration = _seconds(status)
                clock = _clock(elapsed) + (f" / {_clock(duration)}" if duration else "")
                drawn = skin.text(surface, clock, (box.right, y), body, "dim", align="right")
                fraction = elapsed / duration if duration else 0.0
                self._lamp_row(surface, box.x, drawn.x - gap, y, height, fraction)
            elif what == "volume":
                drawn = skin.text(surface, t("nowplaying.volume"), (box.x, y), body, "dim")
                self._lamp_row(surface, drawn.right + gap, box.right, y, height, int(volume) / 100)
            elif what == "state":
                skin.text(surface, t(_STATES.get(state, "status.stop")), (box.x, y), body, "alert")
            else:
                text = t("nowplaying.next", song=library.song_label(upcoming))
                skin.text(surface, text, (box.x, y), body, "dim", max_width=box.w)
            y += height + gap

    def _lamp_row(self, surface, left: int, right: int, y: int, height: int, fraction: float):
        width = right - left
        if width >= 24:
            count = max(4, min(20, width // max(8, height)))
            self.skin.lamps(surface, pygame.Rect(left, y, width, height), progress(count, fraction))


_STATES = {"play": "status.play", "pause": "status.pause", "stop": "status.stop"}


class MenuScene(Scene):
    # Each option's label is the catalog's "menu.<option>".
    OPTIONS = ["audio", "info", "inputtest", "update", "language", "install", "back"]

    def __init__(self, app):
        super().__init__(app)
        self.index = 0
        self.options = self._options()
        self.notice: str | None = None  # why the last option failed, shown below the list

    @staticmethod
    def _options() -> list[str]:
        # The installer clones the USB stick; on a rocola already installed on a disk it
        # has nothing to clone from, so the option only shows up in the live system.
        live = sysinfo.is_live()
        return [opt for opt in MenuScene.OPTIONS if opt != "install" or live]

    def on_enter(self) -> None:
        self.index = 0
        self.notice = None
        self.options = self._options()

    def handle(self, action: str) -> None:
        if action == actions.UP:
            self.index = (self.index - 1) % len(self.options)
        elif action == actions.DOWN:
            self.index = (self.index + 1) % len(self.options)
        elif action in (actions.BACK, actions.MENU):
            self.app.set_scene("library")
        elif action == actions.SELECT:
            self._activate(self.options[self.index])

    def _activate(self, key: str) -> None:
        if key == "audio":
            self.app.set_scene("audio")
        elif key == "info":
            self.app.set_scene("info")
        elif key == "inputtest":
            self.app.set_scene("inputtest")
        elif key == "update":
            self.app.mpd_safe(lambda c: c.update())
            self.app.set_scene("library")
        elif key == "language":
            self.notice = None
            self.app.change_language(i18n.next_language(i18n.language()))
        elif key == "install":
            self.notice = self.app.launch_installer()
        else:
            self.app.set_scene("library")

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        skin = self.skin
        skin.panel(surface)
        self.app.draw_header(surface, t("header.menu"))
        size, small = max(18, h // 16), max(14, h // 26)
        top = self.app.header_h + 8
        notice_h = skin.line_height(small) + 10 if self.notice else 0
        # On a short screen (320×240 at 15 kHz) the gaps shrink, then the letters, so the
        # last option and the notice are never left below the bottom edge.
        pitch = min(skin.line_height(size) + 14, (h - top - notice_h - 4) // len(self.options))
        size = skin.shrink_to(size, pitch)
        slack = h - top - notice_h - pitch * len(self.options)
        y = top + max(0, min(h // 6 - 8, slack // 2))
        for i, key in enumerate(self.options):
            selected = i == self.index
            tone = "alert" if selected else "normal"
            prefix = "> " if selected else "  "
            skin.text(surface, prefix + t(f"menu.{key}"), (w // 2, y), size, tone, align="center")
            y += pitch
        if self.notice:
            skin.text(
                surface, self.notice, (w // 2, y + 10), small, "alert", "body", w - 32, "center"
            )


class AudioScene(Scene):
    """Selector de salida de audio: lista los *sinks* de PipeWire y permite elegir uno
    (lo prueba con un tono). Incluye un acceso para emparejar un dispositivo Bluetooth.
    """

    def __init__(self, app):
        super().__init__(app)
        self.sinks: list[audio.Sink] = []
        self.index = 0
        self.top = 0
        self.available = True

    def on_enter(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.available = audio.available()
        self.sinks = audio.list_sinks() if self.available else []
        self.index = max(0, min(self.index, self._count() - 1))

    def _count(self) -> int:
        # sinks + la fila "Emparejar Bluetooth…" (siempre presente)
        return len(self.sinks) + 1

    def _is_pair_row(self, i: int) -> bool:
        return i == len(self.sinks)

    def handle(self, action: str) -> None:
        if not self.available:
            # draw() corta acá mostrando "PipeWire no responde… Reintentá": damos a
            # Enter ese sentido (re-chequear) y a Esc volver. Sin esta guarda, Enter
            # caía en _select() y, con la lista de sinks vacía, la fila "Emparejar
            # Bluetooth" es el índice 0 → saltaba a emparejar sin que nadie lo pidiera.
            if action in (actions.BACK, actions.MENU):
                self.app.set_scene("menu")
            elif action == actions.SELECT:
                self.refresh()
            return
        if action == actions.UP:
            self.index = (self.index - 1) % self._count()
        elif action == actions.DOWN:
            self.index = (self.index + 1) % self._count()
        elif action == actions.SELECT:
            self._select()
        elif action in (actions.BACK, actions.MENU):
            self.app.set_scene("menu")

    def _select(self) -> None:
        if self._is_pair_row(self.index):
            self.app.set_scene("btpair")
            return
        if 0 <= self.index < len(self.sinks):
            sink = self.sinks[self.index]
            if audio.set_default(sink.name):
                audio.play_test_tone(sink.name)
            self.refresh()

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        skin = self.skin
        skin.panel(surface)
        self.app.draw_header(surface, t("header.audio"))

        size = max(16, h // 18)
        line_h = skin.line_height(size) + 8
        top_y = self.app.header_h + 8
        rows = max(1, (h - top_y - 2 * line_h) // line_h)  # reservar 1 línea para el hint

        if not self.available:
            text = t("audio.unavailable")
            skin.text(surface, text, (16, top_y), size, "alert", max_width=w - 32)
            return

        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + rows:
            self.top = self.index - rows + 1

        total = self._count()
        for i in range(self.top, min(self.top + rows, total)):
            y = top_y + (i - self.top) * line_h
            selected = i == self.index
            if selected:
                skin.cursor_bar(surface, pygame.Rect(8, y - 2, w - 16, line_h))
            tone = "selected" if selected else "normal"
            if self._is_pair_row(i):
                text = t("audio.pair")
            else:
                s = self.sinks[i]
                # Marcador ASCII para el sink actual: el tema puede no traer una
                # fuente con glifos no-ASCII (●/○ tofu con la fuente de fallback).
                marker = "* " if s.is_default else "  "
                text = f"{marker}[{s.kind}] {s.description}"
            skin.text(surface, text, (16, y), size, tone, max_width=w - 32)

        self._hint(surface, t("audio.hint"))


class InfoScene(Scene):
    """Información / diagnóstico del sistema (sólo lectura)."""

    def __init__(self, app):
        super().__init__(app)
        self.rows: list[tuple[str, str]] = []

    def on_enter(self) -> None:
        self.rows = sysinfo.collect(self.app.screen)

    def handle(self, action: str) -> None:
        if action in (actions.BACK, actions.SELECT, actions.MENU):
            self.app.set_scene("menu")

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        skin = self.skin
        skin.panel(surface)
        self.app.draw_header(surface, t("header.info"))

        size = max(15, h // 22)
        line_h = skin.line_height(size) + 10
        col = max(180, w // 3)
        x = 16
        y = self.app.header_h + 12
        for label, value in self.rows:
            skin.text(surface, f"{label}:", (x, y), size, "alert", max_width=col - 8)
            skin.text(surface, str(value), (x + col, y), size, max_width=w - x - col - 16)
            y += line_h

        self._hint(surface, t("info.hint"))


def describe_event(event) -> str | None:
    """What an input event is, in the words rocola.toml uses ([keys] names, [buttons] indexes)."""
    if event.type == pygame.KEYDOWN:
        return t("input.key", name=pygame.key.name(event.key))
    if event.type == pygame.JOYBUTTONDOWN:
        return t("input.button", joy=event.joy, button=event.button)
    if event.type == pygame.JOYHATMOTION:
        if tuple(event.value) == (0, 0):
            return None
        return t("input.hat", joy=event.joy, value=event.value)
    if event.type == pygame.JOYAXISMOTION:
        return t("input.axis", joy=event.joy, axis=event.axis, value=event.value)
    return None


class InputTestScene(Scene):
    """Muestra qué manda cada tecla o botón y qué acción le toca, para armar [keys]/[buttons].

    Recibe TODOS los eventos de input por record() (la app no le pasa acciones), así se
    puede probar también Atrás. Se sale con Atrás dos veces seguidas o tras IDLE_EXIT_S
    sin tocar nada: con un encoder mal mapeado nadie tiene que quedar atrapado acá.
    """

    IDLE_EXIT_S = 15.0
    MAX_LINES = 8

    def __init__(self, app):
        super().__init__(app)
        self.lines: list[str] = []
        self.last_action: str | None = None
        self.last_input = time.monotonic()

    def on_enter(self) -> None:
        self.lines = []
        self.last_action = None
        self.last_input = time.monotonic()

    def record(self, event, action: str | None) -> None:
        desc = describe_event(event)
        if desc is None or (event.type == pygame.JOYAXISMOTION and action is None):
            return  # centro de la cruceta, o un eje que sigue apretado
        self.last_input = time.monotonic()
        self.lines.append(f"{desc}  ->  {action or t('input.no_action')}")
        del self.lines[: -self.MAX_LINES]
        if action == actions.BACK and self.last_action == actions.BACK:
            self.app.set_scene("menu")
        self.last_action = action

    def draw(self, surface) -> None:
        if time.monotonic() - self.last_input > self.IDLE_EXIT_S:
            self.app.set_scene("menu")
            return
        w, h = surface.get_size()
        skin = self.skin
        skin.panel(surface)
        self.app.draw_header(surface, t("header.inputtest"))

        size = max(15, h // 22)
        line_h = skin.line_height(size) + 8
        y = self.app.header_h + 12
        skin.text(surface, t("input.intro"), (16, y), size, "dim", max_width=w - 32)
        y += line_h + 6
        hint_top = h - skin.line_height(max(13, h // 26)) - 6
        fits = max(1, (hint_top - y) // line_h)  # the newest ones, as many as fit
        for line in (self.lines or [t("input.waiting")])[-fits:]:
            skin.text(surface, line, (16, y), size, max_width=w - 32)
            y += line_h

        self._hint(surface, t("input.hint", seconds=round(self.IDLE_EXIT_S)))


class BtPairScene(Scene):
    """Emparejamiento Bluetooth con los controles de arcade (flechas + Enter).

    Escanea con `bluetoothctl` (vía bt.py), lista los dispositivos y empareja/conecta
    el elegido — sin VT ni root (reemplaza al viejo botón que abría una TUI con openvt).
    Máquina de estados manejada por tiempo en draw() (no hay hook de update por frame).
    """

    SCAN_SECS = 12

    def __init__(self, app):
        super().__init__(app)
        self.state = "init"
        self.devices: list[tuple[str, str]] = []
        self.index = 0
        self.top = 0
        self.scan_proc = None
        self.scan_start = 0.0
        self.last_poll = 0.0
        self.pending = ("", "")  # (mac, nombre) a emparejar
        self.pair_thread = None  # emparejado en background (no congela el loop)
        self.pair_result = None  # resultado de bt.pair_connect (lo setea el thread)
        self.pair_start = 0.0
        self.result_msg = ""

    def on_enter(self) -> None:
        self.devices = []
        self.index = 0
        self.top = 0
        self.pending = ("", "")
        self.pair_thread = None
        self.pair_result = None
        self.result_msg = ""
        if not bt.available():
            self.state = "noadapter"
            return
        bt.power_on()
        self.scan_proc = bt.start_scan(self.SCAN_SECS)
        self.scan_start = time.time()
        self.last_poll = 0.0
        self.state = "scanning"

    def _finish_scan(self) -> None:
        bt.stop_scan(self.scan_proc)
        self.scan_proc = None

    def handle(self, action: str) -> None:
        if self.state in ("scanning", "list"):
            if action in (actions.BACK, actions.MENU):
                self._finish_scan()
                self.app.set_scene("audio")
            elif not self.devices:
                return
            elif action == actions.UP:
                self.index = (self.index - 1) % len(self.devices)
            elif action == actions.DOWN:
                self.index = (self.index + 1) % len(self.devices)
            elif action == actions.SELECT:
                self._finish_scan()
                self.pending = self.devices[self.index]
                self.pair_thread = None
                self.pair_result = None
                self.state = "pairing"
        elif self.state in ("done", "empty", "noadapter") and action in (
            actions.SELECT,
            actions.BACK,
            actions.MENU,
        ):
            self.app.set_scene("audio")
        # en "pairing" ignoramos el input (está conectando / transicionando)

    @property
    def animating(self) -> bool:  # the countdown and the pairing advance in draw()
        return self.state in ("scanning", "pairing")

    def draw(self, surface) -> None:
        self.skin.panel(surface)
        self.app.draw_header(surface, t("header.bluetooth"))
        now = time.time()

        if self.state == "scanning":
            if now - self.last_poll > 1.0:
                self.last_poll = now
                self.devices = bt.devices()
                self.index = min(self.index, max(0, len(self.devices) - 1))
            if now - self.scan_start >= self.SCAN_SECS:
                self.devices = bt.devices()
                self._finish_scan()
                self.state = "list" if self.devices else "empty"
            remaining = max(0, int(self.SCAN_SECS - (now - self.scan_start)))
            self._draw_list(surface, t("bt.scanning", seconds=remaining))
        elif self.state == "list":
            self._draw_list(surface, t("bt.choose"))
        elif self.state == "pairing":
            # Emparejar en un thread aparte: bt.pair_connect (bluetoothctl pair+trust+
            # connect) tarda 5–30 s y, llamado acá, congelaría el loop de pygame (sin
            # repaint ni input) — parece un cuelgue. Lo corremos en background y vamos
            # mostrando un contador mientras tanto; el loop sigue vivo.
            if self.pair_thread is None:
                mac = self.pending[0]

                def _worker():
                    self.pair_result = bt.pair_connect(mac)

                self.pair_thread = threading.Thread(target=_worker, daemon=True)
                self.pair_thread.start()
                self.pair_start = now
            elapsed = int(now - self.pair_start)
            name = self.pending[1]
            self._draw_message(surface, t("bt.connecting", name=name, seconds=elapsed))
            if not self.pair_thread.is_alive():
                ok = self.pair_result
                self.result_msg = t("bt.connected" if ok else "bt.failed", name=name)
                self.state = "done"
                self.pair_thread = None
        elif self.state == "empty":
            self._draw_message(surface, t("bt.empty"))
        elif self.state == "noadapter":
            self._draw_message(surface, t("bt.noadapter"))
        elif self.state == "done":
            self._draw_message(surface, self.result_msg)

    def _draw_list(self, surface, status: str) -> None:
        w, h = surface.get_size()
        skin = self.skin
        size = max(16, h // 18)
        line_h = skin.line_height(size) + 8
        top_y = self.app.header_h + 8
        skin.text(surface, status, (16, top_y), size, "dim", max_width=w - 32)
        list_y = top_y + line_h
        rows = max(1, (h - list_y - 2 * line_h) // line_h)

        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + rows:
            self.top = self.index - rows + 1

        for i in range(self.top, min(self.top + rows, len(self.devices))):
            y = list_y + (i - self.top) * line_h
            selected = i == self.index
            if selected:
                skin.cursor_bar(surface, pygame.Rect(8, y - 2, w - 16, line_h))
            tone = "selected" if selected else "normal"
            skin.text(surface, self.devices[i][1], (16, y), size, tone, max_width=w - 32)

        self._hint(surface, t("bt.hint"))

    def _draw_message(self, surface, text: str) -> None:
        w, h = surface.get_size()
        size = max(18, h // 16)
        y = self.app.header_h + h // 6
        for line in text.split("\n"):
            drawn = self.skin.text(
                surface, line, (w // 2, y), size, max_width=w - 32, align="center"
            )
            y += drawn.height + 8
