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


class MPDClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 6600, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._file = None

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

    # --- E/S de bajo nivel -----------------------------------------------
    def _send(self, command: str) -> List[Tuple[str, str]]:
        if not self._file:
            raise MPDError("no conectado")
        self._file.write((command + "\n").encode("utf-8"))
        self._file.flush()
        pairs: List[Tuple[str, str]] = []
        while True:
            raw = self._file.readline()
            if not raw:
                raise MPDError("conexión cerrada")
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line == "OK":
                return pairs
            if line.startswith("ACK"):
                raise MPDError(line)
            if ": " in line:
                key, val = line.split(": ", 1)
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

    def clear(self) -> None:
        self._send("clear")

    def add(self, uri: str) -> None:
        self._send(f'add "{_esc(uri)}"')

    def play_uri(self, uri: str) -> None:
        """Encola y reproduce un archivo enseguida."""
        self._send(f'addid "{_esc(uri)}"')
        self.play()


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
