"""The marquee's lamps: they run for a moment when a song starts, and rest lit."""

from __future__ import annotations

import threading
import time

import pygame
import pytest

from rocola import app as rapp
from rocola import config, ui
from rocola.config import Config
from rocola.effects import EffectsGovernor
from rocola.skin import Skin, chase
from rocola.theme import Theme


class FakeApp:
    motion_only = False
    song_started = None
    booted_at = None
    attract = False
    BOOT_S = 1.0

    def __init__(self, level="completo"):
        self.theme = Theme.load(Config().theme_dir)
        self.skin = Skin(self.theme)
        self.effects = EffectsGovernor(level)
        self.state = {"song": {}, "status": {}, "cover": None}

    def marquee_title(self):
        return "ROCOLA"

    def button_label(self, action):
        return ""


@pytest.fixture
def screen():
    pygame.init()
    surface = pygame.display.set_mode((640, 480))
    yield surface
    pygame.quit()


def test_chase_moves_one_lamp_in_three():
    assert chase(7, 0) == [True, False, False, True, False, False, True]
    assert chase(7, 1) == [False, True, False, False, True, False, False]


def test_the_lamps_run_when_a_song_starts_and_then_rest():
    app = FakeApp()
    scene = ui.NowPlayingScene(app)
    lamps, step_ms = app.skin.chaser()
    assert (lamps, step_ms) == (16, 120)  # what Ámbar asks for
    assert not scene.animating
    assert scene._lamps() == [True] * lamps  # resting: all lit

    app.song_started = time.monotonic() - 0.25  # two steps of 120 ms ago
    assert scene.animating
    assert scene._lamps() == chase(lamps, 2)

    app.song_started = time.monotonic() - ui.JukeboxScene.CHASE_S["completo"]
    assert not scene.animating
    assert scene._lamps() == [True] * lamps


def test_with_the_effects_off_the_lamps_never_run():
    app = FakeApp("apagado")
    app.song_started = time.monotonic()
    assert not ui.LibraryScene(app).animating


def test_a_frame_where_only_the_lamps_move_sends_only_them(screen):
    app = FakeApp()
    scene = ui.LibraryScene(app)
    scene.draw(screen)
    _marquee, lamps, rest = scene._layout(screen)
    screen.fill((255, 0, 255), rest)  # anything drawn below the lamps must stay as it is
    app.song_started = time.monotonic()
    app.motion_only = True
    assert scene.draw(screen) == [lamps]
    assert tuple(screen.get_at(rest.center))[:3] == (255, 0, 255)
    assert tuple(screen.get_at((lamps.x + 1, lamps.y + 1)))[:3] == app.theme.color("background")


class FakeMPD:
    connected = True

    def __init__(self):
        self.song = {}
        self.playing = "play"

    def status(self):
        return {"state": self.playing}

    def current_song(self):
        return dict(self.song)

    def cover_art(self, uri):
        return None

    def stats(self):
        return {"db_update": "1"}


def test_the_app_notes_when_a_new_song_starts_playing():
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)
    app.mpd = FakeMPD()
    app.state = {"song": {}, "status": {}, "cover": None}
    app._cover_uri = None
    app._db_update = None
    app._last_stats = 0.0
    app.scenes = {}
    app.dirty = False

    def poll():
        app._last_poll = 0.0
        app._poll_state()

    poll()
    assert app.song_started is None  # nothing in the queue
    app.mpd.song = {"file": "a.mp3"}
    poll()
    first = app.song_started
    assert first is not None
    poll()
    assert app.song_started == first  # the same song goes on: no new start
    app.mpd.song, app.mpd.playing = {"file": "b.mp3"}, "pause"
    poll()
    assert app.song_started == first  # a song that does not play does not light anything


def test_the_loop_draws_only_the_lamps_while_they_run_then_a_still_frame(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "USER_CONFIG", tmp_path / "missing.toml")
    monkeypatch.setattr(config, "DISPLAY_CONF", tmp_path / "missing.conf")
    for name, value in {
        "ROCOLA_MPD_PORT": "1",
        "ROCOLA_RES": "320x240",
        "ROCOLA_WINDOWED": "1",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ROCOLA_SCREENSHOT", raising=False)
    monkeypatch.setattr(rapp.RocolaApp, "HEARTBEAT_S", 30.0)
    monkeypatch.setattr(ui.JukeboxScene, "CHASE_S", {"completo": 0.4})
    monkeypatch.setattr(rapp.RocolaApp, "BOOT_S", 0.05)  # lit almost at once

    frames = []
    real = ui.LibraryScene.draw

    def draw(self, surface):
        frames.append(self.app.motion_only)
        return real(self, surface)

    monkeypatch.setattr(ui.LibraryScene, "draw", draw)
    app = rapp.RocolaApp()
    start = app.set_scene

    def set_scene(name):
        start(name)
        app.song_started = time.monotonic()

    monkeypatch.setattr(app, "set_scene", set_scene)

    def quit_later():
        time.sleep(1.0)
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    threading.Thread(target=quit_later, daemon=True).start()
    app.run()
    assert frames[0] is False  # the first frame, whole
    assert frames.count(True) >= 3  # the lamps running, alone
    assert frames[-1] is False and frames[-2] is True  # and once they stop, the still frame


def playing(state="play"):
    app = FakeApp()
    app.state = {
        "song": {"file": "a.mp3", "Title": "Uno", "Artist": "Alguien"},
        "status": {"state": state, "volume": "60", "elapsed": "30", "duration": "120"},
        "cover": None,
        "next": {"file": "b.mp3", "Title": "Dos", "Artist": "Alguien"},
    }
    return app


def test_the_record_turns_by_the_clock_and_stops_when_paused(screen, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: now[0])
    app = playing()
    scene = ui.NowPlayingScene(app)
    scene.draw(screen)
    assert scene.animating
    assert scene._angle() == 0
    now[0] += 0.04  # 45 rpm: a rotated label (9°) every thirtieth of a second
    assert scene._angle() == 1
    now[0] += 0.13
    assert scene._angle() == 5
    app.state["status"]["state"] = "pause"
    scene.draw(screen)  # the poll that brings the pause also asks for a frame
    now[0] += 10
    assert scene._angle() == 5  # paused: it stays where it was
    assert not scene.animating
    app.state["status"]["state"] = "play"
    assert scene._angle() == 5
    now[0] += 0.04
    assert scene._angle() == 6  # and goes on from there


def test_with_the_effects_off_the_record_stays_still(screen):
    app = playing()
    app.effects = EffectsGovernor("apagado")
    scene = ui.NowPlayingScene(app)
    scene.draw(screen)
    assert not scene.animating


def test_while_it_plays_a_frame_sends_only_the_lamps_and_the_record(screen):
    app = playing()
    scene = ui.NowPlayingScene(app)
    scene.draw(screen)
    lamps = scene._layout(screen)[1]
    record = scene._record_rect
    app.motion_only = True
    assert scene.draw(screen) == [lamps, record]


def test_now_playing_shows_how_far_the_volume_and_what_comes_next(screen):
    app = playing("pause")
    texts = []
    real = app.skin.text
    app.skin.text = lambda surface, text, *a, **k: (
        texts.append(text) or real(surface, text, *a, **k)
    )
    ui.NowPlayingScene(app).draw(screen)
    assert texts == [
        "Uno",
        "Alguien",
        "0:30 / 2:00",
        "Volumen",
        "En pausa",
        "A continuación: Alguien — Dos",
    ]


def test_the_app_asks_for_the_next_song_only_when_the_queue_changes():
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)
    app.state = {"next": {}}
    app.dirty = False
    asked = []

    class MPD:
        def song_at(self, pos):
            asked.append(pos)
            return {"file": f"{pos}.mp3"}

    app.mpd = MPD()
    app._update_next({"playlist": "5", "nextsong": "3"})
    app._update_next({"playlist": "5", "nextsong": "3"})
    assert asked == [3] and app.state["next"] == {"file": "3.mp3"}
    app._update_next({"playlist": "6"})  # the last song of the queue: nothing next
    assert asked == [3] and app.state["next"] == {}


def test_the_legend_puts_each_button_number_on_its_cap(monkeypatch):
    from rocola import input as actions

    app = rapp.RocolaApp.__new__(rapp.RocolaApp)
    assert app.button_label(actions.SELECT) == ""  # no controls known: plain caps
    app.input = actions.InputManager()  # the default map: Select is button 0, Menu 3
    assert [app.button_label(a) for a in (actions.SELECT, actions.MENU, actions.UP)] == [
        "0",
        "3",
        "",
    ]
    scene = ui.LibraryScene(app)
    items = scene._legend_items()
    assert [control for control, _cap, _text in items] == [
        "stick_v",
        "stick_h",
        "button",
        "button",
        "button",
    ]
    assert [(cap, text) for _c, cap, text in items][2:] == [
        ("0", "Elegir"),
        ("1", "Atrás"),
        ("3", "Menú"),
    ]


def test_the_legend_leaves_out_what_does_not_fit(screen):
    app = FakeApp()
    items = [("button", "0", "Elegir")] * 10
    rect = pygame.Rect(10, 400, 200, 20)
    drawn = app.skin.legend(screen, rect, items)
    assert rect.contains(drawn) and drawn.w > 0
    assert app.skin.legend(screen, pygame.Rect(10, 400, 5, 20), items).w == 0


def test_now_playing_says_play_when_it_is_paused():
    app = playing("pause")
    assert ui.NowPlayingScene(app)._legend_items()[0][2] == "Seguir"
    app.state["status"]["state"] = "play"
    assert ui.NowPlayingScene(app)._legend_items()[0][2] == "Pausa"
