"""Escenas de la UI: biblioteca, now-playing y menú.

Render simple (pensado para 320x240 / 640x480 en CRT y resoluciones mayores en
VGA/moderno). Cada escena maneja acciones (ver input.py) y se dibuja sobre la
superficie principal.
"""
from __future__ import annotations

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
        if key == "update":
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
