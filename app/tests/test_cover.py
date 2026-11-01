"""Cover art: MPD's binary answers, one fetch per song, and the now playing screen."""

from __future__ import annotations

import pygame
import pytest

from rocola import ui
from rocola.app import RocolaApp
from rocola.mpdclient import MPDClient, MPDError

URI = "Queen/Opera/01.mp3"


def chunk(data: bytes, size: int, extra: list[str] | None = None) -> bytes:
    """An MPD binary answer: size, other pairs, binary length, the bytes, newline, OK."""
    head = [f"size: {size}", *(extra or []), f"binary: {len(data)}"]
    return ("\n".join(head) + "\n").encode() + data + b"\nOK\n"


def connect(fake_mpd, responses):
    srv = fake_mpd(responses)
    client = MPDClient("127.0.0.1", srv.port, timeout=2.0)
    client.connect()
    return client, srv


def png_bytes(tmp_path, size=(40, 20), color=(200, 30, 30)) -> bytes:
    pygame.init()
    surf = pygame.Surface(size)
    surf.fill(color)
    path = tmp_path / "cover.png"
    pygame.image.save(surf, str(path))
    return path.read_bytes()


def test_cover_is_read_in_chunks_from_the_folder_file(fake_mpd):
    data = bytes(range(256)) * 5  # binary, with newlines and "OK" lookalikes inside
    client, srv = connect(
        fake_mpd,
        {
            f'albumart "{URI}" 0': chunk(data[:1000], len(data)),
            f'albumart "{URI}" 1000': chunk(data[1000:], len(data)),
        },
    )
    assert client.cover_art(URI) == data
    assert srv.commands == [
        "binarylimit 1048576",
        f'albumart "{URI}" 0',
        f'albumart "{URI}" 1000',
    ]
    assert client.status() == {}  # the connection is still in sync


def test_embedded_picture_when_the_folder_has_no_cover(fake_mpd):
    client, srv = connect(
        fake_mpd,
        {
            f'albumart "{URI}" 0': "ACK [50@0] {albumart} No file exists",
            f'readpicture "{URI}" 0': chunk(b"PIC", 3, ["type: image/png"]),
        },
    )
    assert client.cover_art(URI) == b"PIC"


def test_no_cover_at_all(fake_mpd):
    # readpicture answers a plain OK when the song has no picture.
    client, _ = connect(fake_mpd, {f'albumart "{URI}" 0': "ACK [50@0] {albumart} No file exists"})
    assert client.cover_art(URI) is None


def test_covers_bigger_than_the_limit_are_skipped(fake_mpd):
    client, srv = connect(fake_mpd, {f'albumart "{URI}" 0': chunk(b"x" * 10, 5000)})
    assert client.cover_art(URI, limit=1000) is None
    assert f'albumart "{URI}" 10' not in srv.commands


def test_old_mpd_without_binarylimit_or_cover_commands(fake_mpd):
    client, srv = connect(
        fake_mpd,
        {
            "binarylimit 1048576": 'ACK [5@0] {} unknown command "binarylimit"',
            f'albumart "{URI}" 0': 'ACK [5@0] {} unknown command "albumart"',
            f'readpicture "{URI}" 0': 'ACK [5@0] {} unknown command "readpicture"',
        },
    )
    assert client.cover_art(URI) is None
    client.cover_art(URI)
    assert srv.commands.count("binarylimit 1048576") == 1  # once per connection


def test_a_cut_binary_answer_fails_like_a_dead_connection(fake_mpd):
    # Fewer bytes than announced: the read times out (OSError), and the app drops the
    # connection and reconnects, as with any other MPD failure.
    srv = fake_mpd({f'albumart "{URI}" 0': b"size: 10\nbinary: 10\nabc"})
    client = MPDClient("127.0.0.1", srv.port, timeout=0.2)
    client.connect()
    with pytest.raises((MPDError, OSError)):
        client.cover_art(URI)


@pytest.fixture
def polled_app(fake_mpd, monkeypatch):
    def start(responses):
        srv = fake_mpd({"status": ["state: play"], "stats": ["db_update: 1"], **responses})
        monkeypatch.setenv("ROCOLA_MPD_PORT", str(srv.port))
        app = RocolaApp()
        app.scenes = {}

        def poll():
            app._last_poll = 0.0
            app._poll_state()

        return app, srv, poll

    return start


def test_cover_is_fetched_once_per_song(polled_app):
    app, srv, poll = polled_app(
        {"currentsong": [f"file: {URI}"], f'albumart "{URI}" 0': chunk(b"IMG", 3)}
    )
    poll()
    poll()
    assert app.state["cover"] == b"IMG"
    assert srv.commands.count(f'albumart "{URI}" 0') == 1

    srv.responses["currentsong"] = []  # stopped: no song, no cover
    poll()
    assert app.state["cover"] is None


class FakeApp:
    header_h = 48

    def __init__(self, theme, state):
        self.theme = theme
        self.state = state

    def draw_header(self, surface, subtitle=""):
        pass


@pytest.fixture
def screen():
    pygame.init()
    surface = pygame.display.set_mode((640, 480))
    yield surface
    pygame.quit()


def theme():
    from rocola.config import Config
    from rocola.theme import Theme

    return Theme.load(Config().theme_dir)


def test_now_playing_draws_the_cover_on_the_left(screen, tmp_path):
    state = {
        "song": {"file": URI, "Title": "Death on Two Legs", "Artist": "Queen"},
        "status": {"state": "play", "volume": "70"},
        "cover": png_bytes(tmp_path, (40, 20), (200, 30, 30)),
    }
    scene = ui.NowPlayingScene(FakeApp(theme(), state))
    scene.draw(screen)
    # Fitted in a square of side min(480-48-32, (640-48)*2//5) = 236: 236x118, centered.
    assert scene._cover_img.get_size() == (236, 118)
    assert tuple(screen.get_at((16 + 100, 48 + 16 + 200)))[:3] == (200, 30, 30)
    cached = scene._cover_img
    scene.draw(screen)
    assert scene._cover_img is cached  # decoded once, not every frame


def test_now_playing_without_a_readable_cover(screen):
    state = {"song": {"file": URI, "Title": "T"}, "status": {}, "cover": b"not an image"}
    scene = ui.NowPlayingScene(FakeApp(theme(), state))
    scene.draw(screen)
    assert scene._cover_img is None
