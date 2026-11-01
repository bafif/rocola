from __future__ import annotations

import pygame
import pytest

from rocola import input as rin


def ev(kind, **attrs):
    return pygame.event.Event(kind, attrs)


@pytest.fixture
def im():
    return rin.InputManager()


def test_keyboard(im):
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_UP)) == rin.UP
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_RETURN)) == rin.SELECT
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_F10)) == rin.MENU
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_q)) is None
    assert im.translate(ev(pygame.KEYUP, key=pygame.K_UP)) is None


def test_buttons(im):
    assert im.translate(ev(pygame.JOYBUTTONDOWN, joy=0, button=0)) == rin.SELECT
    assert im.translate(ev(pygame.JOYBUTTONDOWN, joy=0, button=7)) == rin.VOLUP
    assert im.translate(ev(pygame.JOYBUTTONDOWN, joy=0, button=42)) is None


@pytest.mark.parametrize(
    ("value", "action"),
    [
        ((0, 1), rin.UP),
        ((0, -1), rin.DOWN),
        ((-1, 0), rin.LEFT),
        ((1, 0), rin.RIGHT),
        ((0, 0), None),
    ],
)
def test_hat(im, value, action):
    assert im.translate(ev(pygame.JOYHATMOTION, joy=0, hat=0, value=value)) == action


def test_axis_fires_once_per_push(im):
    def axis(axis, value):
        return im.translate(ev(pygame.JOYAXISMOTION, joy=0, axis=axis, value=value))

    assert axis(1, 0.2) is None  # inside the dead zone
    assert axis(1, 0.9) == rin.DOWN
    assert axis(1, 1.0) is None  # still held: no repeat
    assert axis(1, 0.0) is None  # back to center
    assert axis(1, -0.8) == rin.UP
    assert axis(0, -0.8) == rin.LEFT  # even axes are horizontal
    assert axis(0, 0.0) is None
    assert axis(0, 0.8) == rin.RIGHT


def test_custom_maps():
    im = rin.InputManager(keymap={pygame.K_a: rin.NEXT}, buttonmap={9: rin.BACK})
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_a)) == rin.NEXT
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_UP)) is None
    assert im.translate(ev(pygame.JOYBUTTONDOWN, joy=0, button=9)) == rin.BACK


@pytest.fixture
def pg():
    pygame.init()
    yield
    pygame.quit()


def test_build_keymap_overrides(pg, capsys):
    keymap = rin.build_keymap(
        {"a": "next", "f10": "none", "space": "menu", "nosuchkey": "up", "b": "fly"}
    )
    assert keymap[pygame.K_a] == rin.NEXT
    assert pygame.K_F10 not in keymap  # "none" removes a default
    assert keymap[pygame.K_SPACE] == rin.MENU  # overrides a default
    assert keymap[pygame.K_UP] == rin.UP  # untouched defaults stay
    assert pygame.K_b not in keymap  # unknown action is skipped
    err = capsys.readouterr().err
    assert "nosuchkey" in err and "fly" in err


def test_build_buttonmap_overrides():
    buttonmap = rin.build_buttonmap({8: "menu", 3: "none", 0: "back"})
    assert buttonmap[8] == rin.MENU
    assert 3 not in buttonmap
    assert buttonmap[0] == rin.BACK
    assert buttonmap[7] == rin.VOLUP
    assert rin.build_buttonmap(None) == rin.DEFAULT_BUTTONMAP


def test_empty_maps_stay_empty():
    im = rin.InputManager(keymap={}, buttonmap={})
    assert im.translate(ev(pygame.KEYDOWN, key=pygame.K_UP)) is None
    assert im.translate(ev(pygame.JOYBUTTONDOWN, joy=0, button=0)) is None
