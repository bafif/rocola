#!/usr/bin/env python3
"""fake-mpd.py — a pretend MPD with a sample library, for the captures of theme-shots.sh.

Answers what the jukebox asks at start (status, currentsong, stats, listallinfo) with made-up
artists and songs (with accents and eñes, to see them in the theme's fonts), and nothing else:
no covers, no playing. Writes the port it listens on to <portfile> and quits after 30 seconds
with no one connecting.

Use: fake-mpd.py <portfile> [many|one]   (many artists: index cards; one: song cards)
"""

from __future__ import annotations

import socket
import sys

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


def answers(songs: list[dict[str, str]]) -> dict[str, list[str]]:
    listing = [f"{key}: {value}" for song in songs for key, value in song.items()]
    first = [f"{key}: {value}" for key, value in songs[0].items()]
    return {
        "status": ["volume: 80", "state: play", "song: 0", "elapsed: 42.0", "duration: 180.0"],
        "currentsong": first,
        "stats": [f"songs: {len(songs)}", "db_update: 1762819200"],
        "listallinfo": listing,
    }


def serve(conn: socket.socket, replies: dict[str, list[str]]) -> None:
    with conn, conn.makefile("rwb") as f:
        f.write(b"OK MPD 0.23.5\n")
        f.flush()
        for raw in f:
            command = raw.decode("utf-8").strip()
            name = command.split(" ", 1)[0]
            if name in ("albumart", "readpicture"):  # no covers
                f.write(f"ACK [50@0] {{{name}}} No file exists\n".encode())
            else:
                for line in replies.get(name, []):
                    f.write((line + "\n").encode("utf-8"))
                f.write(b"OK\n")
            f.flush()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    replies = answers(library(argv[1] if len(argv) > 1 else "many"))
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
            serve(conn, replies)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
