"""The library reloads by itself when MPD's database changes (e.g. a USB import)."""

from __future__ import annotations

import pytest

from rocola.app import RocolaApp


class CountingLibrary:
    def __init__(self) -> None:
        self.refreshes = 0

    def refresh(self) -> None:
        self.refreshes += 1


@pytest.fixture
def app_and_server(fake_mpd, monkeypatch):
    srv = fake_mpd({"status": ["state: stop"], "currentsong": [], "stats": ["db_update: 100"]})
    monkeypatch.setenv("ROCOLA_MPD_PORT", str(srv.port))
    app = RocolaApp()
    lib = CountingLibrary()
    app.scenes = {"library": lib}
    return app, srv, lib


def poll(app: RocolaApp) -> None:
    app._last_poll = 0.0
    app._last_stats = 0.0
    app._poll_state()


def test_refreshes_only_when_db_update_changes(app_and_server):
    app, srv, lib = app_and_server
    poll(app)
    assert lib.refreshes == 1  # connect
    poll(app)
    assert lib.refreshes == 1  # same database
    srv.responses["stats"] = ["db_update: 200"]
    poll(app)
    assert lib.refreshes == 2
    poll(app)
    assert lib.refreshes == 2
