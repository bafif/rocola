"""Browse the library by artist and album.

Everything is built from the one `listallinfo` listing the library scene already loads,
so browsing never sends extra commands to MPD. Pure functions, no pygame: the scene in
ui.py only draws the views built here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

UNKNOWN_ARTIST = "(sin artista)"
UNKNOWN_ALBUM = "(sin álbum)"
ALL_SONGS = "Todas las canciones"

Song = dict[str, str]


def artist_of(song: Song) -> str:
    """Grouping artist: AlbumArtist keeps a compilation together, else Artist."""
    return (song.get("AlbumArtist") or song.get("Artist") or "").strip()


def album_of(song: Song) -> str:
    return (song.get("Album") or "").strip()


def _number(value: str | None) -> int:
    """Leading number of a Track/Disc tag ("3", "3/12", "03"); 0 when there is none."""
    match = re.match(r"\s*(\d+)", value or "")
    return int(match.group(1)) if match else 0


def _year(song: Song) -> int:
    match = re.match(r"\s*(\d{4})", song.get("Date") or "")
    return int(match.group(1)) if match else 0


def _name_order(name: str) -> tuple[bool, str]:
    return (name == "", name.casefold())  # untagged groups go last


def _group(songs: Iterable[Song], key) -> dict[str, list[Song]]:
    groups: dict[str, list[Song]] = {}
    for song in songs:
        groups.setdefault(key(song), []).append(song)
    return groups


def by_artist(songs: Iterable[Song]) -> list[tuple[str, list[Song]]]:
    """(artist, songs) pairs sorted by name, case-insensitively; untagged last."""
    return sorted(_group(songs, artist_of).items(), key=lambda kv: _name_order(kv[0]))


def by_album(songs: Iterable[Song]) -> list[tuple[str, list[Song]]]:
    """(album, tracks) pairs, oldest first (by Date), then by name; untagged last."""

    def order(item: tuple[str, list[Song]]):
        name, tracks = item
        years = [y for y in map(_year, tracks) if y]
        return (name == "", min(years) if years else 9999, name.casefold())

    albums = sorted(_group(songs, album_of).items(), key=order)
    return [(name, tracks_in_order(tracks)) for name, tracks in albums]


def tracks_in_order(songs: Iterable[Song]) -> list[Song]:
    def order(song: Song):
        return (_number(song.get("Disc")), _number(song.get("Track")), song.get("file", ""))

    return sorted(songs, key=order)


def _title(song: Song) -> str:
    path = song.get("file", "")
    return song.get("Title") or (path.rsplit("/", 1)[-1] if path else "(desconocido)")


def song_label(song: Song) -> str:
    """The "Artist — Title" label, for lists that mix artists."""
    artist = song.get("Artist")
    return f"{artist} — {_title(song)}" if artist else _title(song)


def track_label(song: Song, album_artist: str) -> str:
    """The "07  Title" label inside an album; the artist only when it is not the album's."""
    title = _title(song)
    artist = song.get("Artist")
    if artist and artist != album_artist:
        title = f"{artist} — {title}"
    number = _number(song.get("Track"))
    return f"{number:02d}  {title}" if number else title


@dataclass
class Row:
    """One line of a view: a folder to open (kind + songs) or a song to play."""

    label: str
    kind: str = "song"  # "song", "all", "artist" or "album"
    songs: list[Song] = field(default_factory=list)
    song: Song | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.label)

    @property
    def is_folder(self) -> bool:
        return self.kind != "song"


@dataclass
class View:
    title: str  # shown in the breadcrumb; "" for the root
    rows: list[Row]
    key: tuple[str, str] | None = None  # the row that opened it (None for the root)
    index: int = 0
    top: int = 0


def _song_rows(songs: Iterable[Song]) -> list[Row]:
    return [Row(song_label(s), song=s) for s in songs]


def _track_rows(tracks: Iterable[Song]) -> list[Row]:
    return [Row(track_label(s, artist_of(s)), song=s) for s in tracks]


def root_view(songs: list[Song]) -> View:
    """Artists, with "Todas las canciones" first. A library with one artist (or none
    tagged) stays the flat list of songs, in MPD's order."""
    artists = by_artist(songs)
    if len(artists) <= 1:
        return View("", _song_rows(songs))
    rows = [Row(ALL_SONGS, "all", list(songs))]
    rows += [Row(name or UNKNOWN_ARTIST, "artist", tracks) for name, tracks in artists]
    return View("", rows)


def open_row(row: Row) -> View:
    """The view a folder row opens. An artist with a single album opens that album."""
    if row.kind == "all":
        return View(row.label, _song_rows(row.songs), row.key)
    if row.kind == "artist":
        albums = by_album(row.songs)
        if len(albums) == 1:
            name, tracks = albums[0]
            return View(f"{row.label} / {name or UNKNOWN_ALBUM}", _track_rows(tracks), row.key)
        everything = [s for _name, tracks in albums for s in tracks]
        rows = [Row(f"Todas de {row.label}", "all", everything)]
        rows += [Row(name or UNKNOWN_ALBUM, "album", tracks) for name, tracks in albums]
        return View(row.label, rows, row.key)
    return View(row.label, _track_rows(row.songs), row.key)  # album: tracks already in order


def reopen(songs: list[Song], path: list[View]) -> list[View]:
    """Rebuild a stack of views over a reloaded library, keeping the user's place.

    Each level is reopened by the key of the row that opened it; where that row is
    gone, the stack stops there. Selections are kept, clamped to the new lengths.
    """
    stack = [root_view(songs)]
    for old in path:
        view = stack[-1]
        if old.key is not None:
            row = next((r for r in view.rows if r.key == old.key), None)
            if row is None:
                break
            view = open_row(row)
            stack.append(view)
        view.index = min(old.index, max(0, len(view.rows) - 1))
        view.top = min(old.top, view.index)
    return stack
