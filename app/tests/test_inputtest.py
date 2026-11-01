"""The "Probar controles" scene: what each input sends, and how to get out of it."""

from __future__ import annotations

import pygame
import pytest

from rocola import input as rin
from rocola import ui


class FakeApp:
    theme = None

    def __init__(self):
        self.scenes: list[str] = []

    def set_scene(self, name: str) -> None:
        self.scenes.append(name)


def ev(kind, **attrs):
    return pygame.event.Event(kind, attrs)


@pytest.fixture
def scene():
    pygame.init()
    s = ui.InputTestScene(FakeApp())
    s.on_enter()
    yield s
    pygame.quit()


def test_describes_keys_and_buttons_like_rocola_toml(scene):
    scene.record(ev(pygame.KEYDOWN, key=pygame.K_F10), rin.MENU)
    scene.record(ev(pygame.JOYBUTTONDOWN, joy=0, button=8), None)
    scene.record(ev(pygame.JOYHATMOTION, joy=0, hat=0, value=(0, 1)), rin.UP)
    assert scene.lines == [
        "Tecla «f10»  ->  menu",
        "Joystick 0 · botón 8  ->  sin acción",
        "Joystick 0 · cruceta (0, 1)  ->  up",
    ]
    # the key name shown is the one [keys] accepts
    assert pygame.key.key_code("f10") == pygame.K_F10


def test_ignores_hat_release_and_held_axis(scene):
    scene.record(ev(pygame.JOYHATMOTION, joy=0, hat=0, value=(0, 0)), None)
    scene.record(ev(pygame.JOYAXISMOTION, joy=0, axis=1, value=0.9), None)
    assert scene.lines == []
    scene.record(ev(pygame.JOYAXISMOTION, joy=0, axis=1, value=0.9), rin.DOWN)
    assert scene.lines == ["Joystick 0 · eje 1 (+0.9)  ->  down"]


def test_keeps_only_the_last_lines(scene):
    for button in range(20):
        scene.record(ev(pygame.JOYBUTTONDOWN, joy=0, button=button), None)
    assert len(scene.lines) == scene.MAX_LINES
    assert scene.lines[-1].startswith("Joystick 0 · botón 19")


def test_back_twice_in_a_row_returns_to_menu(scene):
    back = ev(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    scene.record(back, rin.BACK)
    scene.record(ev(pygame.JOYBUTTONDOWN, joy=0, button=9), None)  # breaks the pair
    scene.record(back, rin.BACK)
    assert scene.app.scenes == []
    scene.record(back, rin.BACK)
    assert scene.app.scenes == ["menu"]


def test_idle_timeout_returns_to_menu(scene, monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(ui.time, "monotonic", lambda: t[0])
    scene.on_enter()
    t[0] += scene.IDLE_EXIT_S + 1
    scene.draw(None)  # leaves before touching the surface
    assert scene.app.scenes == ["menu"]
