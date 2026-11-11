"""Every scene, with every theme and at every size a jukebox runs at: no text falls off."""

from __future__ import annotations

import pygame
import pytest

from rocola import app as rapp
from rocola import audio, bt, library, ui
from rocola.config import ASSETS_DIR
from rocola.effects import EffectsGovernor
from rocola.skin import Skin
from rocola.theme import Theme

# The size each kind of display usually runs at, and the kind.
SCREENS = [((320, 240), "crt15"), ((640, 480), "crt"), ((720, 576), "tv"), ((1280, 720), "lcd")]
THEMES = sorted(p.parent.name for p in (ASSETS_DIR / "themes").glob("*/theme.toml"))
CASES = [(size, display, theme) for theme in THEMES for size, display in SCREENS]
IDS = [f"{theme}-{display}" for _size, display, theme in CASES]

SONGS = [
    {
        "file": f"m/{i}.mp3",
        "Artist": f"Artista con un nombre bastante largo {i % 3}",
        "Album": f"Un disco cuyo título no entra en ninguna pantalla chica {i % 2}",
        "Title": f"Canción número {i} con un título larguísimo para probar el corte",
    }
    for i in range(40)
]


def make_app(size, display, theme):
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)  # no MPD, no loop
    app.theme = Theme.load(ASSETS_DIR / "themes" / theme, display)
    app.skin = Skin(app.theme)
    app.effects = EffectsGovernor()
    app.state = {  # paused, with a next song: the most lines "Now playing" can show
        "song": SONGS[0],
        "status": {"state": "pause", "volume": "100", "elapsed": "61", "duration": "245"},
        "cover": None,
        "next": SONGS[1],
    }
    app.scenes = {}
    app.screen = pygame.display.get_surface()
    return app


def scenes(app, monkeypatch):
    monkeypatch.setattr(audio, "available", lambda: True)
    sinks = [
        audio.Sink(f"alsa_output.usb-{i}", f"Salida de audio con descripción muy larga {i}", i == 0)
        for i in range(12)
    ]
    monkeypatch.setattr(audio, "list_sinks", lambda: sinks)
    monkeypatch.setattr(ui.sysinfo, "collect", lambda screen: [("Etiqueta larga", "x" * 200)] * 9)
    monkeypatch.setattr(ui.sysinfo, "is_live", lambda: True)
    monkeypatch.setattr(bt, "available", lambda: False)

    lib = ui.LibraryScene(app)
    lib.songs = SONGS
    lib.stack = library.reopen(SONGS, lib.stack)
    lib.stack.append(library.open_row(lib.view.rows[1]))
    out = {"library": lib, "nowplaying": ui.NowPlayingScene(app), "menu": ui.MenuScene(app)}
    out["menu"].notice = "No se pudo abrir el instalador: " + "motivo largo " * 10
    out["audio"] = ui.AudioScene(app)
    out["info"] = ui.InfoScene(app)
    tester = ui.InputTestScene(app)
    tester.lines = ["Tecla: return  ->  select"] * 12
    out["inputtest"] = tester
    out["btpair"] = ui.BtPairScene(app)
    return out


@pytest.mark.parametrize(("size", "display", "theme"), CASES, ids=IDS)
def test_no_scene_cuts_text(size, display, theme, monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode(size)
    app = make_app(size, display, theme)
    bounds = app.theme.safe_rect(size)  # inside the margin of the display, not just the screen
    cut = []
    real, real_legend = app.skin.text, app.skin.legend

    def recorded(surface, text, *args, **kwargs):
        rect = real(surface, text, *args, **kwargs)
        if not bounds.contains(rect):
            cut.append(f"{name}: {text[:30]!r} at {tuple(rect)}")
        return rect

    def legend(surface, rect, items):
        drawn = real_legend(surface, rect, items)
        if not bounds.contains(drawn) or len(items) and not drawn.w:
            cut.append(f"{name}: legend at {tuple(drawn)}")
        return drawn

    app.skin.text = recorded
    app.skin.legend = legend
    for name, scene in scenes(app, monkeypatch).items():
        if name in ("audio", "info", "btpair"):
            scene.on_enter()
        scene.draw(screen)
    pygame.quit()
    assert not cut


@pytest.mark.parametrize(("size", "display", "theme"), CASES, ids=IDS)
def test_the_selector_shows_a_page_of_cards_inside_the_safe_area(size, display, theme, monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode(size)
    app = make_app(size, display, theme)
    safe = app.theme.safe_rect(size)
    cards = []
    real = app.skin.card

    def recorded(surface, rect, code, *args, **kwargs):
        cards.append((code, pygame.Rect(rect)))
        return real(surface, rect, code, *args, **kwargs)

    app.skin.card = recorded
    lib = scenes(app, monkeypatch)["library"]
    lib.stack = lib.stack[:1]  # the artists: "All songs" and three of them
    lib.songs = SONGS * 3  # and on an album, more songs than fit on a page
    lib.stack = library.reopen(lib.songs, lib.stack)
    lib.stack.append(library.open_row(lib.view.rows[0]))
    lib.draw(screen)
    pygame.quit()
    columns, rows = app.theme.profile.cards
    assert [code for code, _r in cards] == [f"A{i}" for i in range(1, columns * rows + 1)]
    rects = [r for _c, r in cards]
    assert all(safe.contains(r) for r in rects)
    assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1 :])
    assert len({r.x for r in rects}) == columns  # two columns, A1 at the top of the left one
    assert rects[1].y > rects[0].y and rects[rows].x > rects[0].x
