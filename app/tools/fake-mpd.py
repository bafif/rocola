#!/usr/bin/env python3
"""fake-mpd.py — a pretend MPD with a sample library, for the captures of theme-shots.sh.

Answers what the jukebox asks at start (status, currentsong, stats, listallinfo, the next song
in the queue and the cover) with made-up artists and songs (with accents and eñes, to see them
in the theme's fonts) and a cover drawn here, and nothing else: it plays nothing. Writes the
port it listens on to <portfile> and quits after 30 seconds with no one connecting.

Use: fake-mpd.py <portfile> [many|one]   (many artists: index cards; one: song cards)
"""

from __future__ import annotations

import socket
import struct
import sys
import zlib

ARTISTS = [
    "Ñandú Eléctrico",
    "Orquesta Típica del Puerto",
    "María Pérez y Los Cósmicos",
    "Los Faroles de Avellaneda",
    "Trío Lúcuma",
    "Cuarteto Ámbar",
    "La Sonora del Domingo",
    "Hermanos Quiñones",
    "Valeria Sur",
    "Los Pibes del Andén",
    "Banda Municipal de Tilcara",
    "Coro Bajo Cero",
    "Ulises y la Ronda",
]
TITLES = [
    "Milonga del último tranvía",
    "¿Quién apagó la luz?",
    "Canción para un año bisiesto",
    "Ñoquis del 29",
    "Vals de la vereda",
    "El tren de las 6:40",
    "Zamba de la radio vieja",
]


def library(kind: str) -> list[dict[str, str]]:
    artists = ARTISTS[:1] if kind == "one" else ARTISTS
    per_album = 14 if kind == "one" else 3
    songs = []
    for a, artist in enumerate(artists):
        for album in range(1 if kind == "one" else 2):
            for track in range(per_album):
                title = TITLES[(a + album + track) % len(TITLES)]
                songs.append(
                    {
                        "file": f"{artist}/{album}/{track:02d}.mp3",
                        "Artist": artist,
                        "Album": f"Grabaciones de {1950 + a + album * 3}",
                        "Title": title,
                        "Track": str(track + 1),
                        "Date": str(1950 + a + album * 3),
                    }
                )
    return songs


def cover(side: int = 96) -> bytes:
    """A made-up cover as a PNG: rings of the theme-less colors of an old record label."""
    rows = []
    for y in range(side):
        row = bytearray([0])  # no filter
        for x in range(side):
            ring = int(((x - side / 2) ** 2 + (y - side / 2) ** 2) ** 0.5) // (side // 12)
            row += bytes((40, 90, 160) if ring % 2 else (230, 200, 120))
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


def lines(song: dict[str, str]) -> list[str]:
    return [f"{key}: {value}" for key, value in song.items()]


def answers(songs: list[dict[str, str]]) -> dict[str, list[str]]:
    status = ["volume: 80", "state: play", "song: 0", "elapsed: 42.0", "duration: 180.0"]
    status += ["playlist: 2", "nextsong: 1"] if len(songs) > 1 else []
    return {
        "status": status,
        "currentsong": lines(songs[0]),
        "stats": [f"songs: {len(songs)}", "db_update: 1762819200"],
        "listallinfo": [line for song in songs for line in lines(song)],
    }


def serve(conn: socket.socket, replies: dict[str, list[str]], songs, art: bytes) -> None:
    with conn, conn.makefile("rwb") as f:
        f.write(b"OK MPD 0.23.5\n")
        f.flush()
        for raw in f:
            command = raw.decode("utf-8").strip()
            name, _, args = command.partition(" ")
            if name == "albumart":  # the whole cover in one chunk, from any offset
                offset = int(args.rsplit(" ", 1)[-1]) if args else 0
                part = art[offset:]
                f.write(f"size: {len(art)}\nbinary: {len(part)}\n".encode() + part + b"\nOK\n")
            elif name == "readpicture":
                f.write(b"ACK [50@0] {readpicture} No file exists\n")
            else:
                if name == "playlistinfo" and args.isdigit() and int(args) < len(songs):
                    body = lines(songs[int(args)])
                else:
                    body = replies.get(name, [])
                for line in body:
                    f.write((line + "\n").encode("utf-8"))
                f.write(b"OK\n")
            f.flush()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    songs = library(argv[1] if len(argv) > 1 else "many")
    replies, art = answers(songs), cover()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    srv.settimeout(30)
    with open(argv[0], "w", encoding="utf-8") as portfile:
        portfile.write(f"{srv.getsockname()[1]}\n")
    while True:
        try:
            conn, _ = srv.accept()
        except TimeoutError:
            return 0
        conn.settimeout(10)
        try:
            serve(conn, replies, songs, art)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
