"""Escenas de la UI: biblioteca, now-playing y menú.

Render simple (pensado para 320x240 / 640x480 en CRT y resoluciones mayores en
VGA/moderno). Cada escena maneja acciones (ver input.py) y se dibuja sobre la
superficie principal.
"""

from __future__ import annotations

import io
import threading
import time

import pygame

from . import audio, bt, library, sysinfo
from . import input as actions


class Scene:
    def __init__(self, app):
        self.app = app
        self.theme = app.theme

    def on_enter(self) -> None: ...

    def handle(self, action: str) -> None: ...

    def draw(self, surface) -> None: ...


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] if path else "(desconocido)"


def _fit(font, text: str, max_w: int) -> str:
    """`text`, cut with "…" so it is at most `max_w` pixels wide in `font`."""
    if font.size(text)[0] <= max_w:
        return text
    lo, hi = 0, len(text)  # longest prefix that fits, by bisection: few size() calls
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(text[:mid].rstrip() + "…")[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


class LibraryScene(Scene):
    """The library by artist and album (library.py builds the views); selecting a song
    plays it. Back goes up one level, and from the top to the now playing screen."""

    def __init__(self, app):
        super().__init__(app)
        self.songs: list[dict] = []
        self.stack: list[library.View] = [library.View("", [])]
        self.error: str | None = None
        self._labels: dict = {}  # (text, width, color) -> fitted label, for draw()

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

    def handle(self, action: str) -> None:
        view = self.view
        count = len(view.rows)
        if action in (actions.UP, actions.DOWN, actions.LEFT, actions.RIGHT) and count:
            if action == actions.UP:
                view.index = (view.index - 1) % count
            elif action == actions.DOWN:
                view.index = (view.index + 1) % count
            elif action == actions.LEFT:
                view.index = max(0, view.index - 10)
            else:
                view.index = min(count - 1, view.index + 10)
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

    def _label(self, font, text: str, max_w: int, color):
        key = (text, max_w, color)
        img = self._labels.get(key)
        if img is None:
            if len(self._labels) > 256:
                self._labels.clear()
            img = self._labels[key] = font.render(_fit(font, text, max_w), True, color)
        return img

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        bg = self.theme.color("background")
        surface.fill(bg)
        self.app.draw_header(surface, "BIBLIOTECA")

        body = self.theme.font("body", max(16, h // 18))
        line_h = body.get_height() + 6
        top_y = self.app.header_h + 8

        if self.error:
            msg = body.render(f"MPD: {self.error}", True, self.theme.color("accent"))
            surface.blit(msg, (16, top_y))
            return
        if not self.songs:
            msg = body.render(
                "Sin música. Importá canciones (ver menú).", True, self.theme.color("muted")
            )
            surface.blit(msg, (16, top_y))
            return

        view = self.view
        if len(self.stack) > 1:  # breadcrumb: where in the library we are
            path = " / ".join(v.title for v in self.stack[1:])
            surface.blit(self._label(body, path, w - 32, self.theme.color("muted")), (16, top_y))
            top_y += line_h
        rows = max(1, (h - top_y - 8) // line_h)

        # Ventana de scroll que sigue a la selección.
        if view.index < view.top:
            view.top = view.index
        elif view.index >= view.top + rows:
            view.top = view.index - rows + 1

        for i in range(view.top, min(view.top + rows, len(view.rows))):
            row = view.rows[i]
            y = top_y + (i - view.top) * line_h
            selected = i == view.index
            if selected:
                surface.fill(self.theme.color("highlight"), (8, y - 2, w - 16, line_h))
            color = bg if selected else self.theme.color("text")
            text_w = w - 32
            if row.is_folder:  # how many songs it holds, at the right
                count = self._label(
                    body, str(len(row.songs)), w, bg if selected else self.theme.color("muted")
                )
                surface.blit(count, (w - 16 - count.get_width(), y))
                text_w -= count.get_width() + 12
            surface.blit(self._label(body, row.label, text_w, color), (16, y))


def _load_cover(data: bytes, side: int):
    """Decode a cover image and fit it in a `side` x `side` square; None if unreadable."""
    try:
        img = pygame.image.load(io.BytesIO(data))
        if pygame.display.get_surface() is not None:
            img = img.convert()  # display format: faster blits on old hardware
    except (pygame.error, ValueError, OSError):
        return None
    iw, ih = img.get_size()
    if not iw or not ih:
        return None
    scale = side / max(iw, ih)
    size = (max(1, round(iw * scale)), max(1, round(ih * scale)))
    try:
        return pygame.transform.smoothscale(img, size)
    except ValueError:  # smoothscale only takes 24/32-bit surfaces
        return pygame.transform.scale(img, size)


class NowPlayingScene(Scene):
    """What is playing: the cover (if the song has one), title, artist, album, state."""

    MARGIN = 16

    def __init__(self, app):
        super().__init__(app)
        self._cover_src: bytes | None = None  # the bytes the cached image came from
        self._cover_side = 0
        self._cover_img = None

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

    def _cover(self, side: int):
        """The current song's cover scaled to `side`, decoded once per song."""
        data = self.app.state.get("cover")
        if data is not self._cover_src or side != self._cover_side:
            self._cover_src, self._cover_side = data, side
            self._cover_img = _load_cover(data, side) if data else None
        return self._cover_img

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "REPRODUCIENDO")

        song = self.app.state.get("song", {})
        status = self.app.state.get("status", {})
        big = self.theme.font("title", max(22, h // 12))
        body = self.theme.font("body", max(16, h // 20))
        lines = [
            (
                song.get("Title") or (_basename(song["file"]) if song.get("file") else "—"),
                big,
                "text",
            ),
            (song.get("Artist") or "", body, "muted"),
            (song.get("Album") or "", body, "muted"),
            (
                f"[{status.get('state', 'stop')}]   vol {status.get('volume', '?')}%",
                body,
                "accent",
            ),
        ]
        lines = [line for line in lines if line[0]]

        m = self.MARGIN
        area_top = self.app.header_h + m
        area_h = h - area_top - m
        landscape = w >= h
        side = min(area_h, (w - 3 * m) * 2 // 5) if landscape else min(w - 2 * m, area_h // 2)
        cover = self._cover(side) if song.get("file") else None

        if cover is None:  # no cover: the text block, centered
            x, text_w, centered = m, w - 2 * m, True
            y = self.app.header_h + h // 6
        elif landscape:  # cover on the left, text on the right, centered vertically
            surface.blit(cover, (m, area_top + (area_h - cover.get_height()) // 2))
            x = 2 * m + side
            text_w, centered = w - x - m, False
            block = sum(font.get_height() + 10 for _t, font, _c in lines) - 10
            y = area_top + max(0, (area_h - block) // 2)
        else:  # cover on top, text below
            surface.blit(cover, ((w - cover.get_width()) // 2, area_top))
            x, text_w, centered = m, w - 2 * m, True
            y = area_top + cover.get_height() + m

        for text, font, color in lines:
            img = font.render(_fit(font, text, text_w), True, self.theme.color(color))
            surface.blit(img, (x + (text_w - img.get_width()) // 2 if centered else x, y))
            y += img.get_height() + 10


class MenuScene(Scene):
    OPTIONS = [
        ("Salida de audio", "audio"),
        ("Información del sistema", "info"),
        ("Probar controles", "inputtest"),
        ("Actualizar biblioteca", "update"),
        ("Instalar en disco", "install"),
        ("Volver", "back"),
    ]

    def __init__(self, app):
        super().__init__(app)
        self.index = 0

    def on_enter(self) -> None:
        self.index = 0

    def handle(self, action: str) -> None:
        if action == actions.UP:
            self.index = (self.index - 1) % len(self.OPTIONS)
        elif action == actions.DOWN:
            self.index = (self.index + 1) % len(self.OPTIONS)
        elif action in (actions.BACK, actions.MENU):
            self.app.set_scene("library")
        elif action == actions.SELECT:
            self._activate(self.OPTIONS[self.index][1])

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
        elif key == "install":
            self.app.launch_installer()
        else:
            self.app.set_scene("library")

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "MENÚ")
        font = self.theme.font("body", max(18, h // 16))
        y = self.app.header_h + h // 6
        for i, (label, _key) in enumerate(self.OPTIONS):
            selected = i == self.index
            color = self.theme.color("highlight") if selected else self.theme.color("text")
            prefix = "> " if selected else "  "
            img = font.render(prefix + label, True, color)
            surface.blit(img, (w // 2 - img.get_width() // 2, y))
            y += img.get_height() + 14


class AudioScene(Scene):
    """Selector de salida de audio: lista los *sinks* de PipeWire y permite elegir uno
    (lo prueba con un tono). Incluye un acceso para emparejar un dispositivo Bluetooth.
    """

    PAIR_LABEL = "+  Emparejar Bluetooth..."

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
            # Bluetooth" es el índice 0 → saltaba a emparejar sin que el usuario lo pida.
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
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "SALIDA DE AUDIO")

        body = self.theme.font("body", max(16, h // 18))
        line_h = body.get_height() + 8
        top_y = self.app.header_h + 8
        rows = max(1, (h - top_y - 2 * line_h) // line_h)  # reservar 1 línea para el hint

        if not self.available:
            msg = body.render(
                "PipeWire no responde todavía. Reintentá en unos segundos.",
                True,
                self.theme.color("accent"),
            )
            surface.blit(msg, (16, top_y))
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
                surface.fill(self.theme.color("highlight"), (8, y - 2, w - 16, line_h))
            color = self.theme.color("background") if selected else self.theme.color("text")
            if self._is_pair_row(i):
                text = self.PAIR_LABEL
            else:
                s = self.sinks[i]
                # Marcador ASCII para el sink actual: el tema puede no traer una
                # fuente con glifos no-ASCII (●/○ tofu con la fuente de fallback).
                marker = "* " if s.is_default else "  "
                text = f"{marker}[{s.kind}] {s.description}"
            surface.blit(body.render(text, True, color), (16, y))

        hint = self.theme.font("body", max(13, h // 26))
        himg = hint.render(
            "Enter: elegir salida y probar tono   -   Esc: volver", True, self.theme.color("muted")
        )
        surface.blit(himg, (16, h - himg.get_height() - 6))


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
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "INFORMACIÓN")

        font = self.theme.font("body", max(15, h // 22))
        line_h = font.get_height() + 10
        col = max(180, w // 3)
        x = 16
        y = self.app.header_h + 12
        for label, value in self.rows:
            surface.blit(font.render(f"{label}:", True, self.theme.color("accent")), (x, y))
            surface.blit(font.render(str(value), True, self.theme.color("text")), (x + col, y))
            y += line_h

        hint = self.theme.font("body", max(13, h // 26))
        himg = hint.render("Esc: volver", True, self.theme.color("muted"))
        surface.blit(himg, (16, h - himg.get_height() - 6))


def describe_event(event) -> str | None:
    """What an input event is, in the words rocola.toml uses ([keys] names, [buttons] indexes)."""
    if event.type == pygame.KEYDOWN:
        return f"Tecla «{pygame.key.name(event.key)}»"
    if event.type == pygame.JOYBUTTONDOWN:
        return f"Joystick {event.joy} · botón {event.button}"
    if event.type == pygame.JOYHATMOTION:
        return (
            None
            if tuple(event.value) == (0, 0)
            else f"Joystick {event.joy} · cruceta {event.value}"
        )
    if event.type == pygame.JOYAXISMOTION:
        return f"Joystick {event.joy} · eje {event.axis} ({event.value:+.1f})"
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
        self.lines.append(f"{desc}  ->  {action or 'sin acción'}")
        del self.lines[: -self.MAX_LINES]
        if action == actions.BACK and self.last_action == actions.BACK:
            self.app.set_scene("menu")
        self.last_action = action

    def draw(self, surface) -> None:
        if time.monotonic() - self.last_input > self.IDLE_EXIT_S:
            self.app.set_scene("menu")
            return
        w, h = surface.get_size()
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "CONTROLES")

        font = self.theme.font("body", max(15, h // 22))
        line_h = font.get_height() + 8
        y = self.app.header_h + 12
        intro = "Apretá teclas o botones."
        surface.blit(font.render(intro, True, self.theme.color("muted")), (16, y))
        y += line_h + 6
        for line in self.lines or ["Esperando..."]:
            surface.blit(font.render(line, True, self.theme.color("text")), (16, y))
            y += line_h

        hint = self.theme.font("body", max(13, h // 26))
        text = "Volver: Atrás dos veces o 15 s sin tocar nada"
        himg = hint.render(text, True, self.theme.color("muted"))
        surface.blit(himg, (16, h - himg.get_height() - 6))


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

    def draw(self, surface) -> None:
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "BLUETOOTH")
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
            self._draw_list(surface, f"Buscando dispositivos... ({remaining}s)")
        elif self.state == "list":
            self._draw_list(surface, "Elegí un dispositivo (Enter para emparejar):")
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
            self._draw_message(surface, f"Conectando con {self.pending[1]}... ({elapsed}s)")
            if not self.pair_thread.is_alive():
                ok = self.pair_result
                self.result_msg = (
                    f"Conectado: {self.pending[1]}\n\nElegilo como salida (Enter para volver)."
                    if ok
                    else f"No se pudo conectar a {self.pending[1]}.\n\n"
                    "Reintentá (Enter para volver)."
                )
                self.state = "done"
                self.pair_thread = None
        elif self.state == "empty":
            self._draw_message(
                surface,
                "No se encontraron dispositivos.\n\nPoné el parlante en"
                " modo emparejamiento y reintentá (Enter para volver).",
            )
        elif self.state == "noadapter":
            self._draw_message(
                surface,
                "No hay adaptador Bluetooth.\n\nMuchas PCs no traen BT:"
                " conectá un dongle USB (Enter para volver).",
            )
        elif self.state == "done":
            self._draw_message(surface, self.result_msg)

    def _draw_list(self, surface, status: str) -> None:
        w, h = surface.get_size()
        body = self.theme.font("body", max(16, h // 18))
        line_h = body.get_height() + 8
        top_y = self.app.header_h + 8
        surface.blit(body.render(status, True, self.theme.color("muted")), (16, top_y))
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
                surface.fill(self.theme.color("highlight"), (8, y - 2, w - 16, line_h))
            color = self.theme.color("background") if selected else self.theme.color("text")
            surface.blit(body.render(self.devices[i][1], True, color), (16, y))

        hint = self.theme.font("body", max(13, h // 26))
        himg = hint.render("Enter: emparejar   -   Esc: volver", True, self.theme.color("muted"))
        surface.blit(himg, (16, h - himg.get_height() - 6))

    def _draw_message(self, surface, text: str) -> None:
        w, h = surface.get_size()
        font = self.theme.font("body", max(18, h // 16))
        y = self.app.header_h + h // 6
        for line in text.split("\n"):
            img = font.render(line, True, self.theme.color("text"))
            surface.blit(img, (w // 2 - img.get_width() // 2, y))
            y += img.get_height() + 8
