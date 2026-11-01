"""Cliente MPD mínimo por socket (sin dependencias externas).

Implementa lo justo para la rocola: estado, canción actual, control de
reproducción, volumen, y listado de la biblioteca. El protocolo MPD es texto
plano: se envían comandos terminados en '\\n' y se leen líneas 'clave: valor'
hasta 'OK' o 'ACK ...'.
"""

from __future__ import annotations

import socket
from typing import Dict, List, Tuple


class MPDError(Exception):
    pass


class MPDAckError(MPDError):
    """MPD refused the command (an ACK line); the connection is still usable."""


# Biggest cover image the client downloads; a bigger one is skipped.
COVER_LIMIT = 8 * 1024 * 1024


class MPDClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 6600, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._file = None
        self._binary_limit_set = False  # per connection, see _raise_binary_limit

    # --- conexión ---------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._file = self._sock.makefile("rwb")
        hello = self._file.readline().decode("utf-8", "replace")
        if not hello.startswith("OK MPD"):
            self.close()
            raise MPDError(f"saludo inesperado: {hello!r}")

    def close(self) -> None:
        try:
            if self._file:
                self._file.close()
            if self._sock:
                self._sock.close()
        finally:
            self._file = None
            self._sock = None
            self._binary_limit_set = False

    # --- E/S de bajo nivel -----------------------------------------------
    def _send(self, command: str) -> List[Tuple[str, str]]:
        return self._send_binary(command)[0]

    def _send_binary(self, command: str) -> Tuple[List[Tuple[str, str]], bytes]:
        """Like _send, plus the bytes of a `binary: N` answer (albumart, readpicture)."""
        if not self._file:
            raise MPDError("no conectado")
        self._file.write((command + "\n").encode("utf-8"))
        self._file.flush()
        pairs: List[Tuple[str, str]] = []
        data = b""
        while True:
            raw = self._file.readline()
            if not raw:
                raise MPDError("conexión cerrada")
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line == "OK":
                return pairs, data
            if line.startswith("ACK"):
                raise MPDAckError(line)
            if ": " not in line:
                continue
            key, val = line.split(": ", 1)
            if key == "binary":
                # N raw bytes and a newline follow; then the usual OK.
                try:
                    size = int(val)
                except ValueError as exc:
                    raise MPDError(f"respuesta binaria inválida: {line!r}") from exc
                data = self._file.read(size)
                if len(data) < size or not self._file.readline():
                    raise MPDError("conexión cerrada")
                continue
            pairs.append((key, val))

    @staticmethod
    def _as_dict(pairs: List[Tuple[str, str]]) -> Dict[str, str]:
        return {k: v for k, v in pairs}

    def _as_objects(self, pairs: List[Tuple[str, str]], delim: str) -> List[Dict[str, str]]:
        """Agrupa pares en objetos; un nuevo 'delim' empieza un objeto."""
        objs: List[Dict[str, str]] = []
        cur: Dict[str, str] = {}
        for k, v in pairs:
            if k == delim and cur:
                objs.append(cur)
                cur = {}
            cur[k] = v
        if cur:
            objs.append(cur)
        return objs

    # --- comandos de alto nivel ------------------------------------------
    def status(self) -> Dict[str, str]:
        return self._as_dict(self._send("status"))

    def current_song(self) -> Dict[str, str]:
        return self._as_dict(self._send("currentsong"))

    def stats(self) -> Dict[str, str]:
        """Library stats; `db_update` is the time of the last database update."""
        return self._as_dict(self._send("stats"))

    def play(self, pos: int | None = None) -> None:
        self._send(f"play {pos}" if pos is not None else "play")

    def toggle(self) -> None:
        self._send("pause")

    def stop(self) -> None:
        self._send("stop")

    def next(self) -> None:
        self._send("next")

    def previous(self) -> None:
        self._send("previous")

    def set_volume(self, vol: int) -> None:
        self._send(f"setvol {max(0, min(100, vol))}")

    def change_volume(self, delta: int) -> None:
        try:
            cur = int(self.status().get("volume", "50"))
        except ValueError:
            cur = 50
        self.set_volume(cur + delta)

    def update(self) -> None:
        self._send("update")

    def list_artists(self) -> List[str]:
        pairs = self._send("list artist")
        return [v for k, v in pairs if k == "Artist"]

    def list_albums(self, artist: str | None = None) -> List[str]:
        cmd = f'list album artist "{_esc(artist)}"' if artist else "list album"
        return [v for k, v in self._send(cmd) if k == "Album"]

    def find_album(self, album: str) -> List[Dict[str, str]]:
        pairs = self._send(f'find album "{_esc(album)}"')
        return self._as_objects(pairs, "file")

    def all_files(self) -> List[Dict[str, str]]:
        """Listado plano de la biblioteca (puede ser grande)."""
        pairs = self._send("listallinfo")
        return [o for o in self._as_objects(pairs, "file") if "file" in o]

    def cover_art(self, uri: str, limit: int = COVER_LIMIT) -> bytes | None:
        """The cover image of a song, as the bytes of its file (JPEG, PNG...).

        First the cover file of the song's folder (MPD's `albumart`, which looks for
        cover.png/jpg/webp), then the picture embedded in the song (`readpicture`).
        None when there is neither, when it is bigger than `limit`, or when this MPD
        does not know those commands.
        """
        self._raise_binary_limit()
        for command in ("albumart", "readpicture"):
            try:
                data = self._read_binary(command, uri, limit)
            except MPDAckError:
                continue
            if data:
                return data
        return None

    def _raise_binary_limit(self) -> None:
        """Ask for 1 MiB chunks instead of MPD's default 8 KiB: far fewer round trips
        for a big cover on slow hardware. MPD < 0.22.4 refuses it and keeps 8 KiB."""
        if self._binary_limit_set:
            return
        self._binary_limit_set = True
        try:
            self._send("binarylimit 1048576")
        except MPDAckError:
            pass

    def _read_binary(self, command: str, uri: str, limit: int) -> bytes | None:
        data = bytearray()
        while True:  # MPD sends the file in chunks; each request asks from an offset
            pairs, chunk = self._send_binary(f'{command} "{_esc(uri)}" {len(data)}')
            try:
                size = int(self._as_dict(pairs).get("size", "0"))
            except ValueError:
                return None
            if not chunk or size <= 0 or size > limit:
                return None
            data += chunk
            if len(data) >= size:
                return bytes(data)

    def clear(self) -> None:
        self._send("clear")

    def add(self, uri: str) -> None:
        self._send(f'add "{_esc(uri)}"')

    def play_uri(self, uri: str) -> None:
        """Queue a file; if nothing is playing, play that file right away.

        While a song plays the new one just waits its turn in the queue (jukebox).
        Stopped or paused, it starts by id: a bare `play` would resume the paused
        song, or restart the queue from its first song once it has run out.
        """
        song_id = self._as_dict(self._send(f'addid "{_esc(uri)}"')).get("Id")
        if self.status().get("state") == "play":
            return
        self._send(f"playid {song_id}" if song_id else "play")


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
