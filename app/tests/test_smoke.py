"""Render every scene headless (SDL dummy driver) through the app's screenshot mode.

This is the same path the project uses to produce docs/screenshots without a monitor:
it catches import errors, layout crashes and missing assets in each scene.
"""

from __future__ import annotations

import pygame
import pytest

from rocola import audio, bt, i18n, sysinfo
from rocola.app import RocolaApp

LIBRARY = [
    "file: Queen/A Night at the Opera/01 Death on Two Legs.mp3",
    "Artist: Queen",
    "Album: A Night at the Opera",
    "Title: Death on Two Legs",
    "Time: 223",
    "file: Soda Stereo/Canción Animal/01 (En) El Séptimo Día.mp3",
    "Artist: Soda Stereo",
    "Album: Canción Animal",
    "Title: (En) El Séptimo Día",
    "Time: 309",
]
MPD_REPLIES = {
    "status": ["volume: 70", "state: play", "song: 0", "elapsed: 61.2", "duration: 223.0"],
    "currentsong": LIBRARY[:5],
    "listallinfo": LIBRARY,
    "list artist": ["Artist: Queen", "Artist: Soda Stereo"],
    "list album": ["Album: A Night at the Opera", "Album: Canción Animal"],
}


def no_binary(*_args, **_kwargs):
    raise FileNotFoundError


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize(
    "scene", ["library", "nowplaying", "menu", "audio", "info", "btpair", "inputtest"]
)
def test_scene_renders(scene, lang, fake_mpd, monkeypatch, tmp_path):
    srv = fake_mpd(MPD_REPLIES)
    monkeypatch.setenv("ROCOLA_LANG", lang)  # every text of the scene, in each language
    # Never touch the host's PipeWire, BlueZ or network tools from a test.
    for mod in (audio, bt, sysinfo):
        monkeypatch.setattr(mod, "_run", no_binary)
    out = tmp_path / f"{scene}-{lang}.png"
    monkeypatch.setenv("ROCOLA_MPD_PORT", str(srv.port))
    monkeypatch.setenv("ROCOLA_RES", "640x480")
    monkeypatch.setenv("ROCOLA_WINDOWED", "1")
    monkeypatch.setenv("ROCOLA_SCREENSHOT", str(out))
    monkeypatch.setenv("ROCOLA_SCREENSHOT_SCENE", scene)

    RocolaApp().run()

    assert i18n.language() == lang
    assert out.is_file()
    pygame.init()
    try:
        img = pygame.image.load(str(out))
        assert img.get_size() == (640, 480)
    finally:
        pygame.quit()


def test_renders_without_mpd(monkeypatch, tmp_path):
    """MPD down must still give a usable screen (the kiosk boots before MPD answers)."""
    for mod in (audio, bt, sysinfo):
        monkeypatch.setattr(mod, "_run", no_binary)
    monkeypatch.setattr("rocola.app.time.sleep", lambda _s: None)
    out = tmp_path / "nompd.png"
    monkeypatch.setenv("ROCOLA_MPD_PORT", "1")  # nothing listens there
    monkeypatch.setenv("ROCOLA_RES", "320x240")
    monkeypatch.setenv("ROCOLA_WINDOWED", "1")
    monkeypatch.setenv("ROCOLA_SCREENSHOT", str(out))
    RocolaApp().run()
    assert out.is_file()
