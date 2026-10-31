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
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "USER_CONFIG", tmp_path / "missing.toml")
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
