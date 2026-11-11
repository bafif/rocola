"""The jukebox on its own: lighting up at start, and what it does when nobody touches it."""

from __future__ import annotations

import time

import pygame
import pytest

from rocola import app as rapp
from rocola import ui
from rocola.config import Config
from rocola.effects import EffectsGovernor
from rocola.skin import Skin, chase
from rocola.theme import Theme


class Screen:
    def __init__(self):
        self.entered = 0

    def on_enter(self):
        self.entered += 1


def bare_app(scene="library", playing=False):
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)
    app.scenes = {n: Screen() for n in ("library", "nowplaying", "menu", "inputtest", "btpair")}
    app.scene = app.scenes[scene]
    app.state = {"status": {"state": "play" if playing else "stop"}}
    app.dirty = False
    app.last_input = 0.0
    return app


IDLE = rapp.RocolaApp.IDLE_S


def test_with_music_it_goes_to_now_playing_and_the_first_button_comes_back():
    app = bare_app("library", playing=True)
    app._check_idle(IDLE - 1)
    assert app.scene_name() == "library"  # not yet
    app._check_idle(IDLE)
    assert app.scene_name() == "nowplaying" and not app.attract
    assert app._wake()  # the first button only brings the selector back
    assert app.scene_name() == "library"
    assert not app._wake()  # the next one does what it says


def test_without_music_it_invites_and_the_first_button_only_wakes_it():
    app = bare_app("menu")
    app._check_idle(IDLE)
    assert app.attract and app.scene_name() == "library"
    assert app._wake()
    assert not app.attract and app.scene_name() == "menu"


def test_music_that_starts_by_itself_ends_the_invitation():
    app = bare_app("library")
    app._check_idle(IDLE)
    assert app.attract
    app.state["status"]["state"] = "play"  # someone queued a song from elsewhere
    app._check_idle(IDLE + 10)
    assert not app.attract and app.scene_name() == "nowplaying"
    assert app._wake() and app.scene_name() == "library"


@pytest.mark.parametrize("busy", rapp.RocolaApp.NO_IDLE)
def test_screens_with_something_running_are_never_left(busy):
    app = bare_app(busy, playing=True)
    app._check_idle(IDLE * 2)
    assert app.scene_name() == busy and app._resume is None


def test_a_button_while_the_marquee_lights_up_only_skips_it():
    app = bare_app()
    app.booted_at = time.monotonic()
    assert app._wake() and app.booted_at is None
    assert not app._wake()
    app.booted_at = time.monotonic() - 2
    app._check_boot(time.monotonic())
    assert app.booted_at is None  # lit: from here a button does what it says


class FakeApp:
    motion_only = False
    song_started = None
    booted_at = None
    attract = False
    BOOT_S = 1.0

    def __init__(self):
        self.skin = Skin(Theme.load(Config().theme_dir))
        self.effects = EffectsGovernor()
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


def test_the_marquee_lights_up_lamp_after_lamp(screen):
    app = FakeApp()
    scene = ui.LibraryScene(app)
    scene.draw(screen)
    marquee = scene._layout(screen)[0]
    lit = tuple(screen.get_at((marquee.centerx, marquee.y + 2)))[:3]
    app.booted_at = time.monotonic()
    assert scene.animating and scene.fps is None  # the app's own frames, for a smooth light
    scene.draw(screen)
    dark = tuple(screen.get_at((marquee.centerx, marquee.y + 2)))[:3]
    assert sum(dark) < sum(lit) // 4  # almost black at the start
    assert not any(scene._lamps())
    app.booted_at = time.monotonic() - 0.5
    assert scene._lamps() == [i < 8 for i in range(16)]  # half way: half of them


def test_the_attraction_mode_runs_the_lamps_and_invites(screen):
    app = FakeApp()
    app.attract = True
    scene = ui.LibraryScene(app)
    texts = []
    real = app.skin.marquee
    app.skin.marquee = lambda s, r, *text: texts.append(text) or real(s, r, *text)
    scene.draw(screen)
    assert texts == [("¡ELEGÍ UNA CANCIÓN!", "ROCOLA")]  # the invitation, big
    assert scene.animating
    assert scene.fps == 9  # a frame per step of 120 ms, not 30 a second
    step = int(time.monotonic() * 1000) // 120
    assert scene._lamps() in (chase(16, step), chase(16, step + 1))
    app.effects = EffectsGovernor("apagado")
    assert not scene.animating and scene._lamps() == [True] * 16
