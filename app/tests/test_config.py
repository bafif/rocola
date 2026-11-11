from __future__ import annotations

import pytest

from rocola import config
from rocola.config import Config, _parse_res

ENV_VARS = (
    "ROCOLA_MPD_HOST",
    "ROCOLA_MPD_PORT",
    "ROCOLA_THEME",
    "ROCOLA_WINDOWED",
    "ROCOLA_RES",
    "ROCOLA_SCREENSHOT",
    "ROCOLA_SCREENSHOT_SCENE",
    "ROCOLA_DISPLAY",
    "ROCOLA_EFFECTS",
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "USER_CONFIG", tmp_path / "missing.toml")
    monkeypatch.setattr(config, "DISPLAY_CONF", tmp_path / "missing-display.conf")
    return monkeypatch


def write_toml(clean_env, tmp_path, text: str) -> None:
    path = tmp_path / "rocola.toml"
    path.write_text(text, encoding="utf-8")
    clean_env.setattr(config, "USER_CONFIG", path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("640x480", (640, 480)),
        ("720X576", (720, 576)),
        ([320, 240], (320, 240)),
        ("", None),
        (None, None),
        ("640", None),
        ("axb", None),
        ("0x480", None),
        ([1, 2, 3], None),
        (42, None),
    ],
)
def test_parse_res(value, expected):
    assert _parse_res(value) == expected


def test_defaults_without_file_or_env(clean_env):
    cfg = Config.load()
    assert cfg == Config()


def test_env_overrides(clean_env):
    clean_env.setenv("ROCOLA_MPD_HOST", "10.0.0.2")
    clean_env.setenv("ROCOLA_MPD_PORT", "6601")
    clean_env.setenv("ROCOLA_WINDOWED", "1")
    clean_env.setenv("ROCOLA_RES", "640x480")
    clean_env.setenv("ROCOLA_THEME", "neon")
    cfg = Config.load()
    assert (cfg.mpd_host, cfg.mpd_port, cfg.windowed) == ("10.0.0.2", 6601, True)
    assert cfg.resolution == (640, 480)
    assert cfg.theme_dir.name == "neon"


def test_bad_port_env_keeps_default(clean_env):
    clean_env.setenv("ROCOLA_MPD_PORT", "not-a-port")
    assert Config.load().mpd_port == 6600


def test_toml_file_is_read(clean_env, tmp_path):
    write_toml(
        clean_env,
        tmp_path,
        'mpd_port = 6610\nresolution = "720x576"\nwindowed = true\ntheme = "crt"\n',
    )
    cfg = Config.load()
    assert (cfg.mpd_port, cfg.resolution, cfg.windowed, cfg.theme) == (
        6610,
        (720, 576),
        True,
        "crt",
    )


def test_toml_resolution_as_array(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, "resolution = [640, 480]\n")
    assert Config.load().resolution == (640, 480)


def test_toml_bad_values_fall_back(clean_env, tmp_path):
    write_toml(
        clean_env,
        tmp_path,
        'mpd_port = "x"\nfps = true\nresolution = "big"\nwindowed = "yes"\ntheme = 3\n'
        "unknown_key = 1\n",
    )
    cfg = Config.load()
    assert cfg == Config()


def test_broken_toml_is_ignored(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, "this is = = not toml")
    assert Config.load() == Config()


def test_env_wins_over_file(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, "mpd_port = 6610\n")
    clean_env.setenv("ROCOLA_MPD_PORT", "6620")
    assert Config.load().mpd_port == 6620


def test_toml_control_maps(clean_env, tmp_path):
    write_toml(
        clean_env,
        tmp_path,
        '[keys]\nF10 = "none"\nm = " Menu "\nbad = 3\n\n'
        '[buttons]\n8 = "menu"\n"9" = "back"\nx = "up"\n-1 = "up"\n',
    )
    cfg = Config.load()
    assert cfg.keys == {"F10": "none", "m": "menu"}
    assert cfg.buttons == {8: "menu", 9: "back"}


def test_toml_control_maps_wrong_type(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, 'keys = "f10"\nbuttons = [1, 2]\n')
    cfg = Config.load()
    assert cfg.keys == {}
    assert cfg.buttons == {}


def test_display_from_display_conf(clean_env, tmp_path):
    conf = tmp_path / "display.conf"
    conf.write_text('# set by the installer\nMODE="crt15"\nTV_STANDARD=pal\n', encoding="utf-8")
    clean_env.setattr(config, "DISPLAY_CONF", conf)
    assert Config.load().display == "crt15"
    conf.write_text("MODE=vga\n", encoding="utf-8")
    assert Config.load().display == "lcd"


def test_display_and_effects_from_toml_and_env(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, 'display = "TV"\neffects = "soft"\n')
    cfg = Config.load()
    assert (cfg.display, cfg.effects) == ("tv", "suave")
    clean_env.setenv("ROCOLA_DISPLAY", "crt")
    clean_env.setenv("ROCOLA_EFFECTS", "apagado")
    cfg = Config.load()
    assert (cfg.display, cfg.effects) == ("crt", "apagado")


def test_bad_display_and_effects_fall_back(clean_env, tmp_path):
    write_toml(clean_env, tmp_path, 'display = "plasma"\neffects = 2\n')
    clean_env.setenv("ROCOLA_DISPLAY", "oled")
    clean_env.setenv("ROCOLA_EFFECTS", "turbo")
    cfg = Config.load()
    assert (cfg.display, cfg.effects) == ("lcd", "completo")
