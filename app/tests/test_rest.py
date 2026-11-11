"""With nothing moving and nobody touching it, the jukebox barely draws."""

from __future__ import annotations

import threading
import time

import pygame

from rocola import app as rapp
from rocola import config, ui


def test_a_resting_jukebox_draws_almost_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "USER_CONFIG", tmp_path / "missing.toml")
    monkeypatch.setattr(config, "DISPLAY_CONF", tmp_path / "missing.conf")
    for name, value in {
        "ROCOLA_MPD_PORT": "1",  # nothing listens: the library stays empty
        "ROCOLA_RES": "320x240",
        "ROCOLA_WINDOWED": "1",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ROCOLA_SCREENSHOT", raising=False)
    monkeypatch.setattr(rapp.RocolaApp, "HEARTBEAT_S", 0.2)

    draws = []
    real = ui.MenuScene.draw
    monkeypatch.setattr(ui.MenuScene, "draw", lambda self, s: draws.append(1) or real(self, s))
    app = rapp.RocolaApp()
    start = app.set_scene
    monkeypatch.setattr(app, "set_scene", lambda name: start("menu"))

    def quit_later():
        time.sleep(0.7)
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    threading.Thread(target=quit_later, daemon=True).start()
    app.run()
    # The first frame and a heartbeat every 0.2 s; at 30 fps it would be about 20.
    assert 1 <= len(draws) <= 6
    assert app.effects.level == "completo"  # resting frames do not count against the PC
