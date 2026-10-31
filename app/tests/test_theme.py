from __future__ import annotations

import pygame
import pytest

from rocola.config import ASSETS_DIR
from rocola.theme import _DEFAULTS, Theme, _hex


@pytest.fixture(autouse=True, scope="module")
def pygame_font():
    pygame.font.init()
    yield
    pygame.font.quit()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#ff3366", (255, 51, 102)),
        ("00FF00", (0, 255, 0)),
        ("#fff", (1, 2, 3)),
        ("zzzzzz", (1, 2, 3)),
        (None, (1, 2, 3)),
    ],
)
def test_hex(value, expected):
    assert _hex(value, (1, 2, 3)) == expected


def test_missing_theme_dir_uses_defaults(tmp_path):
    theme = Theme.load(tmp_path / "nope")
    assert theme.colors == _DEFAULTS
    assert theme.title == "ROCOLA"
    assert theme.logo() is None


def test_partial_theme_keeps_defaults(tmp_path):
    (tmp_path / "theme.toml").write_text(
        'name = "neon"\n[colors]\naccent = "#00ff00"\nmuted = "bad"\n'
        '[branding]\ntitle = "MI ROCOLA"\n',
        encoding="utf-8",
    )
    theme = Theme.load(tmp_path)
    assert theme.name == "neon"
    assert theme.title == "MI ROCOLA"
    assert theme.color("accent") == (0, 255, 0)
    assert theme.color("muted") == _DEFAULTS["muted"]
    assert theme.color("does-not-exist") == (255, 255, 255)


def test_missing_font_falls_back_and_is_cached(tmp_path):
    (tmp_path / "theme.toml").write_text('[fonts]\ntitle = "missing.ttf"\n', encoding="utf-8")
    theme = Theme.load(tmp_path)
    font = theme.font("title", 20)
    assert isinstance(font, pygame.font.Font)
    assert theme.font("title", 20) is font


def test_bundled_default_theme_loads():
    theme = Theme.load(ASSETS_DIR / "themes" / "default")
    assert theme.name
    assert set(theme.colors) == set(_DEFAULTS)
