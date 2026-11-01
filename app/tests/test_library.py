"""Browsing the library by artist and album (rocola/library.py and the library scene)."""

from __future__ import annotations

from rocola import input as actions
from rocola import library
from rocola.library import Row, View


def song(path, artist=None, album=None, title=None, track=None, **tags):
    s = {"file": path}
    for key, value in (("Artist", artist), ("Album", album), ("Title", title), ("Track", track)):
        if value is not None:
            s[key] = value
    s.update(tags)
    return s


QUEEN_OPERA = [
    song("q/opera/02.mp3", "Queen", "A Night at the Opera", "Lazing on a Sunday", "2/12"),
    song("q/opera/01.mp3", "Queen", "A Night at the Opera", "Death on Two Legs", "1/12"),
]
QUEEN_JAZZ = [song("q/jazz/01.mp3", "Queen", "Jazz", "Mustapha", "1", Date="1978")]
SODA = [song("s/animal/01.mp3", "Soda Stereo", "Canción Animal", "(En) El Séptimo Día", "1")]
UNTAGGED = [song("sueltos/tema01.mp3")]
LIBRARY = QUEEN_JAZZ + SODA + QUEEN_OPERA + UNTAGGED


def labels(view: View) -> list[str]:
    return [row.label for row in view.rows]


def row(view: View, label: str) -> Row:
    return next(r for r in view.rows if r.label == label)


def test_root_lists_artists_case_insensitively_with_untagged_last():
    lib = LIBRARY + [song("a/1.mp3", "abba", "Arrival", "Dancing Queen")]
    root = library.root_view(lib)
    assert labels(root) == [
        library.ALL_SONGS,
        "abba",
        "Queen",
        "Soda Stereo",
        library.UNKNOWN_ARTIST,
    ]
    assert [len(r.songs) for r in root.rows] == [6, 1, 3, 1, 1]


def test_one_artist_or_none_tagged_keeps_the_flat_list_in_mpd_order():
    root = library.root_view(QUEEN_OPERA)
    assert labels(root) == ["Queen — Lazing on a Sunday", "Queen — Death on Two Legs"]
    assert not any(r.is_folder for r in root.rows)
    assert labels(library.root_view(UNTAGGED)) == ["tema01.mp3"]
    assert library.root_view([]).rows == []


def test_all_songs_keeps_mpd_order():
    root = library.root_view(LIBRARY)
    view = library.open_row(row(root, library.ALL_SONGS))
    assert [r.song["file"] for r in view.rows] == [s["file"] for s in LIBRARY]


def test_artist_lists_albums_oldest_first_then_by_name():
    lib = LIBRARY + [song("q/news/01.mp3", "Queen", "News of the World", "We Will Rock You")]
    view = library.open_row(row(library.root_view(lib), "Queen"))
    # Jazz has a Date; the other two do not, so they follow it by name.
    assert labels(view) == [
        "Todas de Queen",
        "Jazz",
        "A Night at the Opera",
        "News of the World",
    ]
    everything = library.open_row(view.rows[0])
    assert [r.song["file"] for r in everything.rows] == [
        "q/jazz/01.mp3",
        "q/opera/01.mp3",
        "q/opera/02.mp3",
        "q/news/01.mp3",
    ]


def test_album_tracks_follow_disc_and_track_numbers():
    view = library.open_row(row(library.root_view(LIBRARY), "Queen"))
    album = library.open_row(row(view, "A Night at the Opera"))
    assert labels(album) == ["01  Death on Two Legs", "02  Lazing on a Sunday"]
    assert album.title == "A Night at the Opera"
    discs = [
        song("x/2-01.mp3", "X", "Live", "Encore", "1", Disc="2"),
        song("x/1-02.mp3", "X", "Live", "Second", "2", Disc="1/2"),
        song("x/1-01.mp3", "X", "Live", "First", "01", Disc="1/2"),
    ]
    assert [s["Title"] for s in library.tracks_in_order(discs)] == ["First", "Second", "Encore"]


def test_artist_with_a_single_album_opens_the_album():
    view = library.open_row(row(library.root_view(LIBRARY), "Soda Stereo"))
    assert view.title == "Soda Stereo / Canción Animal"
    assert labels(view) == ["01  (En) El Séptimo Día"]


def test_compilation_groups_by_album_artist_and_names_each_track_artist():
    comp = [
        song("v/1.mp3", "Charly García", "Rock nacional", "Demoliendo hoteles", "1"),
        song("v/2.mp3", "Spinetta", "Rock nacional", "Muchacha", "2"),
    ]
    for s in comp:
        s["AlbumArtist"] = "Varios"
    root = library.root_view(comp + SODA)
    assert labels(root) == [library.ALL_SONGS, "Soda Stereo", "Varios"]
    album = library.open_row(row(root, "Varios"))
    assert labels(album) == ["01  Charly García — Demoliendo hoteles", "02  Spinetta — Muchacha"]


def test_untagged_songs_get_their_file_name():
    view = library.open_row(row(library.root_view(LIBRARY), library.UNKNOWN_ARTIST))
    assert view.title == f"{library.UNKNOWN_ARTIST} / {library.UNKNOWN_ALBUM}"
    assert labels(view) == ["tema01.mp3"]


def test_reopen_keeps_the_place_and_stops_where_a_level_is_gone():
    root = library.root_view(LIBRARY)
    root.index = 1
    artist = library.open_row(row(root, "Queen"))
    artist.index = 2
    album = library.open_row(row(artist, "A Night at the Opera"))
    album.index = 1
    stack = library.reopen(LIBRARY, [root, artist, album])
    assert [v.title for v in stack] == ["", "Queen", "A Night at the Opera"]
    assert [v.index for v in stack] == [1, 2, 1]

    # The album was deleted: back to Queen, which now has a single album... so the
    # "Queen" row opens Jazz straight away and the stack ends there.
    stack = library.reopen(QUEEN_JAZZ + SODA, [root, artist, album])
    assert [v.title for v in stack] == ["", "Queen / Jazz"]
    assert [v.index for v in stack] == [1, 0]

    assert [v.title for v in library.reopen([], [root, artist])] == [""]


class FakeApp:
    """Just what LibraryScene needs from RocolaApp."""

    def __init__(self, songs):
        self.theme = None
        self.songs = songs
        self.scene = None
        self.played: list[str] = []
        outer = self

        class Client:
            def all_files(self):
                return list(outer.songs)

            def play_uri(self, uri):
                outer.played.append(uri)

        self.mpd = Client()

    def mpd_safe(self, fn):
        fn(self.mpd)

    def set_scene(self, name):
        self.scene = name

    def open_menu(self):
        self.scene = "menu"


def test_scene_goes_down_to_a_song_and_back_up():
    from rocola.ui import LibraryScene

    app = FakeApp(LIBRARY)
    scene = LibraryScene(app)
    scene.on_enter()
    assert labels(scene.view)[1] == "Queen"
    scene.handle(actions.DOWN)
    scene.handle(actions.SELECT)  # Queen
    assert labels(scene.view)[2] == "A Night at the Opera"
    scene.handle(actions.DOWN)
    scene.handle(actions.DOWN)
    scene.handle(actions.SELECT)  # the album
    scene.handle(actions.DOWN)
    scene.handle(actions.SELECT)  # its second track
    assert app.played == ["q/opera/02.mp3"]
    assert app.scene == "nowplaying"

    # Coming back from the now playing screen lands on the same album.
    app.scene = None
    scene.on_enter()
    assert scene.view.title == "A Night at the Opera"
    assert scene.view.index == 1
    scene.handle(actions.BACK)
    scene.handle(actions.BACK)
    assert scene.view.title == ""
    assert app.scene is None
    scene.handle(actions.BACK)  # from the top, Back is the now playing screen
    assert app.scene == "nowplaying"


def test_scene_keeps_the_place_when_mpd_fails():
    from rocola.ui import LibraryScene

    app = FakeApp(LIBRARY)
    scene = LibraryScene(app)
    scene.on_enter()
    scene.handle(actions.DOWN)
    scene.handle(actions.SELECT)

    def broken():
        raise OSError("connection refused")

    app.mpd.all_files = broken
    scene.refresh()
    assert scene.error
    assert scene.view.title == "Queen"


def test_long_labels_are_cut_to_the_width():
    import pygame

    from rocola.ui import _fit

    pygame.font.init()
    font = pygame.font.Font(None, 16)
    text = "We Will Rock You — remastered 2011 version with a very long title"
    fitted = _fit(font, text, 120)
    assert fitted.endswith("…")
    assert font.size(fitted)[0] <= 120
    assert _fit(font, "Jazz", 120) == "Jazz"
