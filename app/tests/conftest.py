"""Shared fixtures: headless SDL and a tiny fake MPD server."""

from __future__ import annotations

import os
import socket
import threading

# pygame must never try to open a real display or audio device in tests.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pytest  # noqa: E402


class FakeMPD:
    """Answers MPD protocol commands from a dict of canned responses.

    `responses` maps a full command line to the body lines (without the final "OK").
    A value starting with "ACK" is sent as the error line instead of "OK".
    Every received command is recorded in `commands`.
    """

    def __init__(self, responses: dict[str, list[str] | str], greeting: str = "OK MPD 0.23.5"):
        self.responses = responses
        self.greeting = greeting
        self.commands: list[str] = []
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(1)
        self.port = self._srv.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        try:
            conn, _ = self._srv.accept()
        except OSError:
            return
        with conn, conn.makefile("rwb") as f:
            f.write((self.greeting + "\n").encode())
            f.flush()
            for raw in f:
                cmd = raw.decode("utf-8").rstrip("\n")
                self.commands.append(cmd)
                reply = self.responses.get(cmd, [])
                if isinstance(reply, str) and reply.startswith("ACK"):
                    f.write((reply + "\n").encode())
                else:
                    for line in reply:
                        f.write((line + "\n").encode("utf-8"))
                    f.write(b"OK\n")
                f.flush()

    def close(self) -> None:
        self._srv.close()


@pytest.fixture
def fake_mpd():
    servers: list[FakeMPD] = []

    def start(responses=None, **kwargs) -> FakeMPD:
        srv = FakeMPD(responses or {}, **kwargs)
        servers.append(srv)
        return srv

    yield start
    for srv in servers:
        srv.close()
