"""The bubble tubes at the sides of the jukebox's screens."""

from __future__ import annotations

import pygame
import pytest

from rocola import ui
from rocola.config import Config
from rocola.effects import EffectsGovernor
from rocola.skin import Skin
from rocola.theme import Theme


class FakeApp:
    motion_only = False
    song_started = None
    booted_at = None
    attract = False
    BOOT_S = 1.0

    def __init__(self, level="completo"):
        self.theme = Theme.load(Config().theme_dir)  # Ámbar: two tubes, 7 bubbles each
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


def test_a_tube_at_each_side_of_what_the_scene_shows(screen):
    app = FakeApp()
    scene = ui.LibraryScene(app)
    _marquee, _lamps, rest, tubes = scene._layout(screen)
    safe = app.skin.safe_rect(screen)
    assert len(tubes) == 2
    left, right = tubes
    assert left.x == safe.x and right.right == safe.right
    assert left.right < rest.x and rest.right < right.x  # the cards keep clear of them
    assert left.h == right.h == rest.h


def test_the_bubbles_rise_by_the_clock_and_stay_still_with_the_effects_off(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: now[0])
    scene = ui.LibraryScene(FakeApp())
    before = scene._bubbles(0)
    assert len(before) == 7
    now[0] += 0.5
    after = scene._bubbles(0)
    assert all(b[1] != a[1] for a, b in zip(before, after))  # every one has moved
    assert all(0 <= x <= 1 and 0 <= y < 1 for x, y in after)
    assert scene.animating and scene.fps == 15

    still = ui.LibraryScene(FakeApp("apagado"))
    first = still._bubbles(0)
    now[0] += 3
    assert still._bubbles(0) == first and not still.animating
    assert ui.LibraryScene(FakeApp("suave")).fps == 8


def test_a_frame_where_only_the_bubbles_move_sends_the_lamps_and_the_tubes(screen):
    app = FakeApp()
    scene = ui.LibraryScene(app)
    scene.draw(screen)
    _marquee, lamps, rest, tubes = scene._layout(screen)
    screen.fill((255, 0, 255), rest)
    app.motion_only = True
    assert scene.draw(screen) == [lamps, *tubes]
    assert tuple(screen.get_at(rest.center))[:3] == (255, 0, 255)  # the cards are not drawn


def test_a_theme_without_tubes_leaves_the_whole_width(screen, tmp_path):
    (tmp_path / "theme.toml").write_text("[effects]\nbubbles = { tubes = 0 }\n", encoding="utf-8")
    app = FakeApp()
    app.skin = Skin(Theme.load(tmp_path))
    _m, _l, rest, tubes = ui.LibraryScene(app)._layout(screen)
    assert tubes == [] and rest.w == app.skin.safe_rect(screen).w
