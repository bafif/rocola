from __future__ import annotations

import ast
from pathlib import Path

import pygame
import pytest

from rocola import skin as rskin
from rocola import ui
from rocola.skin import Record, Skin, progress, ring
from rocola.theme import Theme

COLORS = """
[colors]
background = "#102030"
surface = "#f0e0c0"
text = "#200000"
on_dark = "#ffffff"
accent = "#800000"
glow = "#ffc000"
"""


@pytest.fixture
def screen():
    pygame.init()
    surface = pygame.display.set_mode((320, 240))
    yield surface
    pygame.quit()


def make_skin(tmp_path, extra: str = "") -> Skin:
    (tmp_path / "theme.toml").write_text(COLORS + extra, encoding="utf-8")
    return Skin(Theme.load(tmp_path))


def rgb(surface, pos):
    return tuple(surface.get_at(pos))[:3]


def test_backdrop_is_drawn_once_per_size(screen, tmp_path):
    skin = make_skin(tmp_path)
    skin.backdrop(screen)
    assert rgb(screen, (5, 5)) == (0x10, 0x20, 0x30)
    layer = skin._layers[("backdrop", (320, 240))]
    skin.backdrop(screen)
    assert skin._layers[("backdrop", (320, 240))] is layer
    assert layer.get_bitsize() == screen.get_bitsize()  # already in the screen's format


def test_backdrop_uses_the_cabinet_piece(screen, tmp_path):
    img = pygame.Surface((8, 8))
    img.fill((1, 200, 3))
    pygame.image.save(img, str(tmp_path / "cabinet.png"))
    skin = make_skin(tmp_path, '[pieces]\ncabinet = "cabinet.png"\n')
    skin.backdrop(screen)
    assert rgb(screen, (100, 100)) == (1, 200, 3)


def test_marquee_without_a_piece_is_card_paper(screen, tmp_path):
    skin = make_skin(tmp_path)
    rect = skin.marquee(screen, pygame.Rect(0, 0, 320, 40), "ROCOLA", "MENÚ")
    assert rect == pygame.Rect(0, 0, 320, 40)
    assert rgb(screen, (160, 2)) == (0xF0, 0xE0, 0xC0)
    assert rgb(screen, (160, 39)) == (0x80, 0x00, 0x00)  # the accent rule underneath


def test_text_is_cached_and_aligned(screen, tmp_path):
    skin = make_skin(tmp_path)
    first = skin.render("Hola", 20, "alert")
    assert skin.render("Hola", 20, "alert") is first
    right = skin.text(screen, "Hola", (300, 10), 20, "alert", align="right")
    assert right.right == 300
    center = skin.text(screen, "Hola", (160, 50), 20, align="center")
    assert abs(center.centerx - 160) <= 1


def test_text_is_cut_to_the_width(screen, tmp_path):
    skin = make_skin(tmp_path)
    long = "Una canción con un título larguísimo que no entra en la pantalla"
    assert skin.render(long, 18, max_width=100).get_width() <= 100


def test_card_with_a_cursor(screen, tmp_path):
    skin = make_skin(tmp_path)
    screen.fill((0, 0, 0))
    rect = pygame.Rect(20, 20, 140, 40)
    skin.card(screen, rect, "A1", "Signos", "Soda Stereo", selected=True)
    assert rgb(screen, (rect.right - 3, rect.top + 3)) == (0xF0, 0xE0, 0xC0)  # paper
    assert rgb(screen, (rect.left - 1, rect.centery)) == (0xFF, 0xC0, 0x00)  # the cursor
    assert len(skin._cards) == 1
    skin.card(screen, rect, "A1", "Signos", "Soda Stereo")
    assert len(skin._cards) == 1  # the same card is not drawn again


def test_lamps(screen, tmp_path):
    skin = make_skin(tmp_path)
    screen.fill((0, 0, 0))
    skin.lamps(screen, pygame.Rect(0, 100, 100, 20), [True, False])
    assert rgb(screen, (25, 110)) == (0xFF, 0xC0, 0x00)
    assert rgb(screen, (75, 110)) != (0xFF, 0xC0, 0x00)


def test_ring_and_progress():
    assert ring(6, 4, 3) == [True, False, False, False, True, True]
    assert progress(4, 0.5) == [True, True, False, False]
    assert progress(4, 2.0) == [True] * 4
    assert progress(4, -1) == [False] * 4


def test_record_turns_by_the_clock(screen, tmp_path):
    skin = make_skin(tmp_path)
    cover = pygame.Surface((50, 50))
    cover.fill((0, 0, 255))
    record = skin.record(120, cover)
    assert isinstance(record, Record)
    assert len(record.frames) == Record.FRAMES
    assert record.index(0) == 0
    assert record.index(1 / 30) == 1  # 45 rpm at 30 frames a second: one frame, 9°
    assert record.index(60 / 45) == 0  # a whole turn
    rect = record.draw(screen, (160, 120), record.index(0.5))
    assert rect.size == (120, 120)
    r, g, b = rgb(screen, (160 + 10, 120))  # the cover, as the label (under the shine)
    assert r < 30 and g < 30 and b > 220


def test_scenes_never_name_a_color():
    """The scenes say what goes on screen; only the skin and the theme know how it looks."""
    tree = ast.parse(Path(ui.__file__).read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("color", "theme", "fill", "font"):
            bad.append(f"ui.py:{node.lineno} .{node.attr}")
    assert not bad


def test_tones_name_real_roles():
    from rocola.theme import ROLES

    assert set(rskin.TONES.values()) <= set(ROLES)
