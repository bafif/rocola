"""The menu: the installer option, opening the installer, the now playing status line."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rocola import app as rapp
from rocola import ui


@pytest.mark.parametrize(("live", "shown"), [(True, True), (False, False)])
def test_install_option_only_on_the_usb_stick(monkeypatch, live, shown):
    monkeypatch.setattr(ui.sysinfo, "is_live", lambda: live)
    keys = [key for _label, key in ui.MenuScene._options()]
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
    ("status", "line"),
    [
        ({"state": "play", "volume": "40"}, "Reproduciendo   ·   volumen 40%"),
        ({"state": "pause", "volume": "100"}, "En pausa   ·   volumen 100%"),
        ({"state": "play", "volume": "-1"}, "Reproduciendo"),
        ({}, "Detenido"),
    ],
)
def test_status_line(status, line):
    assert ui._status_line(status) == line
