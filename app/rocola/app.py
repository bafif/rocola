"""RocolaApp — orquestador: inicializa SDL, conecta MPD y corre el loop principal."""
from __future__ import annotations

import os
import subprocess
import time

import pygame

from . import input as rin
from . import ui
from .config import Config
from .mpdclient import MPDClient, MPDError
from .theme import Theme


class RocolaApp:
    def __init__(self) -> None:
        self.config = Config.load()
        self.mpd = MPDClient(self.config.mpd_host, self.config.mpd_port)
        self.input = rin.InputManager()
        self.theme: Theme | None = None
        self.screen = None
        self.clock = None
        self.scenes: dict = {}
        self.scene = None
        self.state: dict = {"song": {}, "status": {}}
        self.header_h = 48
        self.running = False
        self._last_poll = 0.0

    # --- ciclo de vida ----------------------------------------------------
    def run(self) -> None:
        # En el SO la app corre como cliente único de Xorg; en dev, ventana.
        if self.config.windowed:
            os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.init()
        pygame.font.init()

        size = self.config.resolution or (0, 0)  # (0,0) = resolución nativa
        flags = 0 if self.config.windowed else pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Rocola")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        self.theme = Theme.load(self.config.theme_dir)
        self.header_h = max(40, self.screen.get_height() // 10)
        self.input.init_joysticks()
        # En runtime NO bloqueamos esperando a MPD: la UI tiene que dibujar de
        # inmediato (si no, el arranque queda en NEGRO hasta que MPD responde, ~30s
        # en hardware lento). El loop conecta en segundo plano y _on_mpd_connected
        # puebla la biblioteca al conectar. En modo captura sí intentamos 1 vez.
        self._connect_mpd(retries=1 if self.config.screenshot else 0)

        self.scenes = {
            "library": ui.LibraryScene(self),
            "nowplaying": ui.NowPlayingScene(self),
            "menu": ui.MenuScene(self),
        }
        self.set_scene(self.config.screenshot_scene if self.config.screenshot else "library")

        # Modo captura: render de unos frames, guardar PNG y salir (dev/CI).
        if self.config.screenshot:
            self._render_screenshot(self.config.screenshot)
            self._shutdown()
            return

        self.running = True
        while self.running:
            self._handle_events()
            # Dibujar PRIMERO: la UI aparece desde el primer frame, sin esperar a
            # MPD. Recién después sondeamos/(re)conectamos MPD, así un MPD lento o
            # caído no deja la pantalla en negro al arrancar (sólo la congela un
            # instante mientras reintenta, ya con la UI visible).
            if self.scene:
                self.scene.draw(self.screen)
            pygame.display.flip()
            self._poll_state()
            self.clock.tick(self.config.fps)

        self._shutdown()

    def _render_screenshot(self, path: str) -> None:
        """Dibuja la escena y guarda un PNG. Tolera que MPD no esté disponible."""
        self._poll_state()
        for _ in range(3):  # un par de frames para asentar layout/estado
            if self.scene:
                self.scene.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(self.config.fps)
        try:
            pygame.image.save(self.screen, path)
            print(f"[rocola] screenshot guardado en {path}")
        except (OSError, pygame.error) as exc:
            print(f"[rocola] no se pudo guardar screenshot: {exc}")

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type in (
                pygame.KEYDOWN,
                pygame.JOYBUTTONDOWN,
                pygame.JOYAXISMOTION,
                pygame.JOYHATMOTION,
            ):
                action = self.input.translate(event)
                if action and self.scene:
                    self.scene.handle(action)
            elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                self.input.init_joysticks()

    def _shutdown(self) -> None:
        try:
            self.mpd.close()
        finally:
            pygame.quit()

    # --- escenas ----------------------------------------------------------
    def set_scene(self, name: str) -> None:
        scene = self.scenes.get(name)
        if scene is not None:
            self.scene = scene
            scene.on_enter()

    def open_menu(self) -> None:
        self.set_scene("menu")

    # --- MPD --------------------------------------------------------------
    def _connect_mpd(self, retries: int = 30) -> bool:
        for _ in range(retries):
            try:
                self.mpd.connect()
                return True
            except (OSError, MPDError):
                time.sleep(1)
        return False

    def mpd_safe(self, fn) -> None:
        """Ejecuta una operación MPD reconectando si hace falta; nunca crashea la UI."""
        try:
            if not self.mpd.connected:
                self.mpd.connect()
            fn(self.mpd)
        except (OSError, MPDError):
            self.mpd.close()

    def _poll_state(self) -> None:
        now = time.time()
        if now - self._last_poll < 1.0:
            return
        self._last_poll = now
        try:
            if not self.mpd.connected:
                self.mpd.connect()
                self._on_mpd_connected()  # recién conectado: poblar la biblioteca
            self.state["status"] = self.mpd.status()
            self.state["song"] = self.mpd.current_song()
        except (OSError, MPDError):
            self.mpd.close()

    def _on_mpd_connected(self) -> None:
        # Al (re)conectar MPD refrescamos la biblioteca: como la UI arranca sin
        # esperar a MPD, on_enter pudo correr con MPD aún caído y dejarla vacía.
        lib = self.scenes.get("library")
        if lib is not None:
            lib.refresh()

    # --- header (branding) -----------------------------------------------
    def draw_header(self, surface, subtitle: str = "") -> None:
        w = surface.get_width()
        surface.fill(self.theme.color("accent"), (0, 0, w, self.header_h))
        x = 12
        logo = self.theme.logo(max_height=self.header_h - 10)
        if logo:
            surface.blit(logo, (x, 5))
            x += logo.get_width() + 12
        title_font = self.theme.font("title", self.header_h // 2)
        timg = title_font.render(self.theme.title, True, self.theme.color("background"))
        surface.blit(timg, (x, (self.header_h - timg.get_height()) // 2))
        if subtitle:
            sfont = self.theme.font("body", max(14, self.header_h // 3))
            simg = sfont.render(subtitle, True, self.theme.color("background"))
            surface.blit(simg, (w - simg.get_width() - 12, (self.header_h - simg.get_height()) // 2))

    # --- instalador -------------------------------------------------------
    def launch_installer(self) -> None:
        """Lanza el instalador guiado (TUI) en un VT nuevo, best-effort.

        El instalador es whiptail; desde X se abre en otro VT con `openvt`.
        Si no está disponible, vuelve a la biblioteca sin romper nada.
        """
        installer = "/usr/local/bin/rocola-install"
        if os.path.exists(installer):
            try:
                subprocess.Popen(["openvt", "-s", "-w", installer])
            except OSError:
                pass
        self.set_scene("library")
