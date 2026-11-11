"""The menu: the installer option, opening the installer, the now playing status line."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rocola import app as rapp
from rocola import ui


@pytest.mark.parametrize(("live", "shown"), [(True, True), (False, False)])
def test_install_option_only_on_the_usb_stick(monkeypatch, live, shown):
    monkeypatch.setattr(ui.sysinfo, "is_live", lambda: live)
    keys = ui.MenuScene._options()
    assert ("install" in keys) is shown
    assert keys[-1] == "back"


def bare_app() -> rapp.RocolaApp:
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)  # no SDL, no MPD
    app.scenes = {}
    app.scene = None
    return app


def test_launch_installer_starts_the_unit(monkeypatch):
    calls: list = []

    def run(args, **_):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(rapp.subprocess, "run", run)
    assert bare_app().launch_installer() is None
    assert calls == [
        ["systemctl", "start", "--no-block", "--no-ask-password", "rocola-installer.service"]
    ]


def test_launch_installer_failure_is_reported(monkeypatch):
    denied = "Failed to start rocola-installer.service: Access denied"
    monkeypatch.setattr(
        rapp.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(returncode=1, stdout="", stderr=denied),
    )
    assert bare_app().launch_installer() == f"No se pudo abrir el instalador: {denied}"


def test_launch_installer_without_systemctl(monkeypatch):
    def run(*_a, **_k):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(rapp.subprocess, "run", run)
    assert bare_app().launch_installer().startswith("No se pudo abrir el instalador")


@pytest.mark.parametrize(
    ("status", "seconds"),
    [
        ({"elapsed": "61.5", "duration": "185.2"}, (61.5, 185.2)),
        ({"time": "12:180"}, (12.0, 180.0)),  # MPDs before 0.20
        ({"elapsed": "3.0"}, (3.0, 0.0)),  # a stream: no length
        ({}, (0.0, 0.0)),
        ({"elapsed": "x", "time": "bad"}, (0.0, 0.0)),
    ],
)
def test_how_far_the_song_has_gone(status, seconds):
    assert ui._seconds(status) == seconds


def test_clock():
    assert [ui._clock(s) for s in (0, 61.9, 600, -3)] == ["0:00", "1:01", "10:00", "0:00"]
