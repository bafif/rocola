from __future__ import annotations

import pygame
import pytest

from rocola.config import ASSETS_DIR, DISPLAYS
from rocola.theme import FALLBACK_COLORS, PROFILES, ROLES, Theme, mix, parse_color


@pytest.fixture(autouse=True, scope="module")
def pygame_font():
    pygame.font.init()
    yield
    pygame.font.quit()


def bundled_themes() -> list[str]:
    return sorted(p.parent.name for p in (ASSETS_DIR / "themes").glob("*/theme.toml"))


def write_theme(path, text: str):
    path.mkdir(parents=True, exist_ok=True)
    (path / "theme.toml").write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#ff3366", (255, 51, 102)),
        ("00FF00", (0, 255, 0)),
        ("#fff", (1, 2, 3)),
        ("zzzzzz", (1, 2, 3)),
        (None, (1, 2, 3)),
        (7, (1, 2, 3)),
    ],
)
def test_parse_color(value, expected):
    assert parse_color(value, (1, 2, 3)) == expected


def test_missing_theme_is_black_and_white(tmp_path):
    theme = Theme.load(tmp_path / "nope")
    assert theme.colors == FALLBACK_COLORS
    assert theme.title == "ROCOLA"
    assert theme.piece("marquee") is None
    assert theme.color("does-not-exist") == (255, 255, 255)


def test_broken_toml_is_black_and_white(tmp_path, capsys):
    theme = Theme.load(write_theme(tmp_path / "rota", "[colors\nbackground = "), "crt")
    assert theme.colors == FALLBACK_COLORS
    assert theme.display == "crt"
    assert theme.safe_area == PROFILES["crt"].safe_area
    assert "black and white" in capsys.readouterr().err


def test_partial_theme_derives_the_dim_roles(tmp_path):
    theme = Theme.load(
        write_theme(
            tmp_path / "t",
            'name = "Prueba"\n[colors]\nbackground = "#000080"\non_dark = "#ffff00"\n'
            'accent = "bad"\n',
        )
    )
    assert theme.name == "Prueba"
    assert theme.color("accent") == FALLBACK_COLORS["accent"]
    assert theme.color("on_dark_dim") == mix((255, 255, 0), (0, 0, 128), 0.6)
    assert theme.color("text_dim") == FALLBACK_COLORS["text_dim"]  # neither text nor surface


def test_variant_is_laid_over_the_base(tmp_path):
    folder = write_theme(
        tmp_path / "t",
        """
safe_area = 0.04
[colors]
background = "#101010"
glow = "#ffffff"
[fonts]
body = "body.ttf"
digits = "digits.ttf"
[effects]
bubbles = { tubes = 2, per_tube = 7 }
record = { rpm = 45 }
[variant.crt15]
colors.glow = "#ff0000"
fonts.body = "pixel.ttf"
fonts.antialias = false
effects.bubbles = { per_tube = 3 }
[variant.tv]
safe_area = 0.2
""",
    )
    for name in ("body.ttf", "digits.ttf", "pixel.ttf"):
        (folder / name).write_bytes(b"")
    lcd = Theme.load(folder, "lcd")
    crt15 = Theme.load(folder, "crt15")
    tv = Theme.load(folder, "tv")

    assert lcd.color("glow") == (255, 255, 255)
    assert crt15.color("glow") == (255, 0, 0)
    assert crt15.color("background") == (16, 16, 16)  # kept from the base
    assert crt15._fonts["body"].name == "pixel.ttf"
    assert crt15._fonts["digits"].name == "digits.ttf"
    assert (lcd.antialias, crt15.antialias) == (True, False)
    # An effect is replaced whole: the 15 kHz bubbles do not inherit `tubes`.
    assert crt15.effect("bubbles") == {"per_tube": 3}
    assert crt15.effect("record") == {"rpm": 45}
    assert (lcd.safe_area, crt15.safe_area, tv.safe_area) == (0.04, 0.04, 0.2)


def test_unknown_display_is_lcd(tmp_path):
    assert Theme.load(tmp_path, "plasma").display == "lcd"


def test_safe_area_out_of_range_uses_the_profile(tmp_path):
    theme = Theme.load(write_theme(tmp_path / "t", "safe_area = 0.9\n"), "tv")
    assert theme.safe_area == PROFILES["tv"].safe_area
    assert theme.safe_rect((720, 576)) == pygame.Rect(72, 58, 576, 460)


def test_font_falls_back_by_role_and_is_cached(tmp_path):
    folder = write_theme(tmp_path / "t", '[fonts]\nmarquee = "missing.ttf"\n')
    theme = Theme.load(folder)
    font = theme.font("marquee", 40)
    assert isinstance(font, pygame.font.Font)
    assert theme.font("marquee", 40) is font
    assert theme._fonts["marquee"] is None


@pytest.mark.parametrize("display", DISPLAYS)
def test_font_never_smaller_than_the_display_allows(tmp_path, display):
    theme = Theme.load(tmp_path, display)
    small = theme.font("body", 4)
    assert small.get_height() >= theme.font("body", PROFILES[display].min_font).get_height()


def test_piece_nine_slice_keeps_the_corners(tmp_path):
    img = pygame.Surface((30, 30))
    img.fill((0, 0, 255))
    img.fill((255, 0, 0), (0, 0, 10, 10))  # top-left corner
    img.fill((0, 255, 0), (20, 20, 10, 10))  # bottom-right corner
    pygame.image.save(img, str(tmp_path / "card.png"))
    write_theme(tmp_path, '[pieces]\ncard = { file = "card.png", slice = [10, 10, 10, 10] }\n')
    piece = Theme.load(tmp_path).piece("card")
    out = piece.render(100, 50)
    assert out.get_size() == (100, 50)
    assert out.get_at((9, 9))[:3] == (255, 0, 0)
    assert out.get_at((10, 10))[:3] == (0, 0, 255)
    assert out.get_at((90, 40))[:3] == (0, 255, 0)
    assert out.get_at((89, 39))[:3] == (0, 0, 255)
    assert piece.render(100, 50) is out
    assert piece.render(12, 12).get_size() == (12, 12)  # smaller than the corners: scaled


def test_piece_problems_draw_with_colors(tmp_path):
    (tmp_path / "broken.png").write_bytes(b"not a png")
    write_theme(
        tmp_path,
        '[pieces]\nbroken = "broken.png"\nmissing = "nope.png"\n'
        'strip = { file = "broken.png", slice = [1, 2] }\n',
    )
    theme = Theme.load(tmp_path)
    assert theme.piece("broken") is None
    assert theme.piece("missing") is None
    assert theme._pieces["strip"][1] is None  # a bad slice is dropped, the file kept


def test_title_per_language(tmp_path):
    folder = write_theme(
        tmp_path / "t", '[branding]\ntitle = { es = "MI ROCOLA", en = "MY JUKEBOX" }\n'
    )
    theme = Theme.load(folder)
    assert theme.title_for("en") == "MY JUKEBOX"
    assert theme.title_for("pt") == "MI ROCOLA"


def test_ambar_is_the_default_and_has_every_role():
    from rocola.config import Config

    assert Config().theme == "ambar"
    theme = Theme.load(ASSETS_DIR / "themes" / "ambar")
    assert theme.name == "Ámbar"
    assert set(theme.colors) == set(ROLES)
    assert theme.color("background") == (0x24, 0x14, 0x0C)


@pytest.mark.parametrize("display", DISPLAYS)
@pytest.mark.parametrize("name", bundled_themes())
def test_every_bundled_theme_loads_on_every_display(name, display, capsys):
    theme = Theme.load(ASSETS_DIR / "themes" / name, display)
    assert theme.display == display
    assert set(theme.colors) == set(ROLES)
    assert capsys.readouterr().err == ""  # nothing in it was ignored or broken
