"""Escenas de la UI: biblioteca, now-playing y menú.

Render simple (pensado para 320x240 / 640x480 en CRT y resoluciones mayores en
VGA/moderno). Cada escena maneja acciones (ver input.py) y se dibuja sobre la
superficie principal.
"""
from __future__ import annotations

import threading
import time

from . import audio, bt, sysinfo
from . import input as actions


class Scene:
    def __init__(self, app):
        self.app = app
        self.theme = app.theme

    def on_enter(self) -> None:
        ...

    def handle(self, action: str) -> None:
        ...

    def draw(self, surface) -> None:
        ...


def _fmt_song(meta: dict) -> str:
    title = meta.get("Title") or _basename(meta.get("file", ""))
    artist = meta.get("Artist")
    return f"{artist} — {title}" if artist else title


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] if path else "(desconocido)"


class LibraryScene(Scene):
    """Lista plana de la biblioteca; seleccionar reproduce."""

    def __init__(self, app):
        super().__init__(app)
        self.items: list[dict] = []
        self.index = 0
        self.top = 0
        self.error: str | None = None

    def on_enter(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.error = None
        try:
            self.items = self.app.mpd.all_files()
        except Exception as exc:  # noqa: BLE001 - mostrar cualquier fallo en pantalla
            self.items = []
            self.error = str(exc)
        self.index = min(self.index, max(0, len(self.items) - 1))

    def handle(self, action: str) -> None:
        if not self.items:
            if action == actions.MENU:
                self.app.open_menu()
            return
        if action == actions.UP:
            self.index = (self.index - 1) % len(self.items)
        elif action == actions.DOWN:
            self.index = (self.index + 1) % len(self.items)
        elif action == actions.LEFT:
            self.index = max(0, self.index - 10)
        elif action == actions.RIGHT:
            self.index = min(len(self.items) - 1, self.index + 10)
        elif action == actions.SELECT:
            self._play_current()
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
            self.app.set_scene("nowplaying")
        elif action == actions.MENU:
            self.app.open_menu()

    def _play_current(self) -> None:
        uri = self.items[self.index].get("file")
        if uri:
            self.app.mpd_safe(lambda c: c.play_uri(uri))
            self.app.set_scene("nowplaying")

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        bg = self.theme.color("background")
        surface.fill(bg)
        self.app.draw_header(surface, "BIBLIOTECA")

        body = self.theme.font("body", max(16, h // 18))
        line_h = body.get_height() + 6
        top_y = self.app.header_h + 8
        rows = max(1, (h - top_y - 8) // line_h)

        if self.error:
            msg = body.render(f"MPD: {self.error}", True, self.theme.color("accent"))
            surface.blit(msg, (16, top_y))
            return
        if not self.items:
            msg = body.render("Sin música. Importá canciones (ver menú).", True, self.theme.color("muted"))
            surface.blit(msg, (16, top_y))
            return

        # Ventana de scroll centrada en la selección.
        if self.index < self.top:
            self.top = self.index
        elif self.index >= self.top + rows:
            self.top = self.index - rows + 1

        for i in range(self.top, min(self.top + rows, len(self.items))):
            y = top_y + (i - self.top) * line_h
            selected = i == self.index
            if selected:
                surface.fill(self.theme.color("highlight"), (8, y - 2, w - 16, line_h))
            color = bg if selected else self.theme.color("text")
            text = body.render(_fmt_song(self.items[i]), True, color)
            surface.blit(text, (16, y))


class NowPlayingScene(Scene):
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

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(self.theme.color("background"))
        self.app.draw_header(surface, "REPRODUCIENDO")

        song = self.app.state.get("song", {})
        status = self.app.state.get("status", {})

        big = self.theme.font("title", max(22, h // 12))
        body = self.theme.font("body", max(16, h // 20))
        cx = w // 2
        y = self.app.header_h + h // 6

        title = song.get("Title") or _basename(song.get("file", "")) or "—"
        artist = song.get("Artist") or ""
        state = status.get("state", "stop")
        vol = status.get("volume", "?")

        for text, font, color in [
            (title, big, self.theme.color("text")),
            (artist, body, self.theme.color("muted")),
            (f"[{state}]   vol {vol}%", body, self.theme.color("accent")),
        ]:
            img = font.render(text, True, color)
            surface.blit(img, (cx - img.get_width() // 2, y))
            y += img.get_height() + 10


class MenuScene(Scene):
    OPTIONS = [
        ("Salida de audio", "audio"),
        ("Información del sistema", "info"),
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
            msg = body.render("PipeWire no responde todavía. Reintentá en unos segundos.",
                              True, self.theme.color("accent"))
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
        himg = hint.render("Enter: elegir salida y probar tono   -   Esc: volver",
                           True, self.theme.color("muted"))
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
        self.pending = ("", "")     # (mac, nombre) a emparejar
        self.pair_thread = None     # emparejado en background (no congela el loop)
        self.pair_result = None     # resultado de bt.pair_connect (lo setea el thread)
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
        elif self.state in ("done", "empty", "noadapter"):
            if action in (actions.SELECT, actions.BACK, actions.MENU):
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
                    if ok else
                    f"No se pudo conectar a {self.pending[1]}.\n\nReintentá (Enter para volver)."
                )
                self.state = "done"
                self.pair_thread = None
        elif self.state == "empty":
            self._draw_message(surface, "No se encontraron dispositivos.\n\nPoné el parlante en"
                               " modo emparejamiento y reintentá (Enter para volver).")
        elif self.state == "noadapter":
            self._draw_message(surface, "No hay adaptador Bluetooth.\n\nMuchas PCs no traen BT:"
                               " conectá un dongle USB (Enter para volver).")
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
