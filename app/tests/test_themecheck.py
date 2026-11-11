from __future__ import annotations

import pygame
import pytest

from rocola.config import ASSETS_DIR
from rocola.themecheck import check, contrast, luma, main


@pytest.fixture(autouse=True, scope="module")
def pygame_font():
    pygame.font.init()
    yield
    pygame.font.quit()


def bundled() -> list[str]:
    return sorted(p.parent.name for p in (ASSETS_DIR / "themes").glob("*/theme.toml"))


def test_measures():
    assert contrast((0, 0, 0), (255, 255, 255)) == pytest.approx(21)
    assert contrast((10, 10, 10), (10, 10, 10)) == pytest.approx(1)
    assert luma((255, 255, 255)) == pytest.approx(1)
    assert luma((0, 0, 0)) == 0


@pytest.mark.parametrize("name", bundled())
def test_every_bundled_theme_passes(name):
    assert check(ASSETS_DIR / "themes" / name) == []


def test_problems_are_reported(tmp_path):
    (tmp_path / "broken.png").write_bytes(b"not a png")
    (tmp_path / "theme.toml").write_text(
        """
[colors]
background = "#000000"
on_dark = "#333333"
[fonts]
body = "fonts/nope.ttf"
[pieces]
strip = "broken.png"
cabinet = "missing.png"
[variant.tv]
colors.on_dark = "#ffffff"
""",
        encoding="utf-8",
    )
    problems = check(tmp_path)
    assert any(p.startswith("lcd: on_dark on background") for p in problems)
    assert not any(p.startswith("tv: on_dark on background") for p in problems)
    assert "lcd: missing file fonts/nope.ttf" in problems
    assert "lcd: missing file missing.png" in problems
    assert "lcd: piece strip does not load" in problems


def test_broken_or_missing_toml(tmp_path):
    assert check(tmp_path)[0].endswith("no theme.toml")
    (tmp_path / "theme.toml").write_text("[colors\n", encoding="utf-8")
    assert check(tmp_path)[0].startswith("theme.toml:")


def test_main(tmp_path, capsys):
    assert main(["check", "ambar"]) == 0
    assert "ambar: ok" in capsys.readouterr().out
    (tmp_path / "theme.toml").write_text('[colors]\non_dark = "#000000"\n', encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 1
    assert main(["check"]) == 2
