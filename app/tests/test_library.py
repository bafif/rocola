"""Browsing the library by artist and album (rocola/library.py and the library scene)."""

from __future__ import annotations

from rocola import input as actions
from rocola import library
from rocola.i18n import t
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
        t("library.all_songs"),
        "abba",
        "Queen",
        "Soda Stereo",
        t("library.unknown_artist"),
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
    view = library.open_row(row(root, t("library.all_songs")))
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
    assert labels(root) == [t("library.all_songs"), "Soda Stereo", "Varios"]
    album = library.open_row(row(root, "Varios"))
    assert labels(album) == ["01  Charly García — Demoliendo hoteles", "02  Spinetta — Muchacha"]


def test_untagged_songs_get_their_file_name():
    view = library.open_row(row(library.root_view(LIBRARY), t("library.unknown_artist")))
    assert view.title == f"{t('library.unknown_artist')} / {t('library.unknown_album')}"
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

    from rocola.skin import Skin
    from rocola.theme import Theme

    pygame.font.init()
    skin = Skin(Theme())
    text = "We Will Rock You — remastered 2011 version with a very long title"
    fitted = skin.fit(text, 120, 16)
    assert fitted.endswith("…")
    assert skin.font("body", 16).size(fitted)[0] <= 120
    assert skin.fit("Jazz", 120, 16) == "Jazz"


def test_scene_does_not_reload_the_library_on_every_visit():
    from rocola.ui import LibraryScene

    app = FakeApp(LIBRARY)
    calls = []
    real = app.mpd.all_files
    app.mpd.all_files = lambda: calls.append(1) or real()
    scene = LibraryScene(app)
    scene.on_enter()
    scene.on_enter()  # back from the now playing screen
    assert len(calls) == 1
    scene.refresh()  # what the app calls when MPD's database changes
    assert len(calls) == 2


def test_scene_retries_on_enter_after_a_failed_load():
    from rocola.ui import LibraryScene

    app = FakeApp(LIBRARY)
    real = app.mpd.all_files

    def broken():
        raise OSError("connection refused")

    app.mpd.all_files = broken
    scene = LibraryScene(app)
    scene.on_enter()
    assert scene.error
    app.mpd.all_files = real
    scene.on_enter()
    assert scene.error is None
    assert scene.view.rows


def test_codes_follow_the_list_page_by_page():
    assert [library.code(i, 10) for i in (0, 9, 10, 25)] == ["A1", "A10", "B1", "C6"]
    assert library.code(8 * 6, 6) == "J1"  # no I: it reads as a 1
    assert library.code(13 * 6, 6) == "P1"  # no O: it reads as a 0
    assert library.code(24 * 6, 6) == "AA1"  # after Z, two letters
    assert library.code(25 * 6 + 5, 6) == "AB6"


def test_left_and_right_flip_a_whole_page_and_wrap():
    assert library.flip_page(3, 25, 10, 1) == 13
    assert library.flip_page(13, 25, 10, 1) == 23
    assert library.flip_page(23, 25, 10, 1) == 3  # from the last page to the first
    assert library.flip_page(3, 25, 10, -1) == 23
    assert library.flip_page(9, 25, 10, 2) == 24  # the last page is shorter: its last card
    assert library.flip_page(0, 0, 10, 1) == 0


def test_cards_say_title_and_artist_or_how_many_songs():
    root = library.root_view(LIBRARY)
    queen = row(root, "Queen")
    assert library.card_text(queen) == ("Queen", "3 canciones")
    assert library.card_text(row(root, "Soda Stereo")) == ("Soda Stereo", "1 canción")
    album = library.open_row(row(library.open_row(queen), "Jazz"))
    assert library.card_text(album.rows[0]) == ("Mustapha", "Queen")
    assert library.card_text(Row("x", song=UNTAGGED[0])) == ("tema01.mp3", "")


def test_scene_flips_pages_by_the_cards_the_display_shows():
    from rocola.skin import Skin
    from rocola.theme import Theme
    from rocola.ui import LibraryScene

    songs = [song(f"m/{i:02d}.mp3", f"Artista {i:02d}", "Disco", f"Tema {i}") for i in range(25)]
    app = FakeApp(songs)
    app.skin = Skin(Theme(display="tv"))  # 6 cards a page
    scene = LibraryScene(app)
    scene.on_enter()
    scene.handle(actions.DOWN)
    scene.handle(actions.RIGHT)
    assert scene.view.index == 7
    scene.handle(actions.LEFT)
    scene.handle(actions.LEFT)  # from the first page to the last one (26 cards: A1 to E2)
    assert scene.view.index == 25
    assert library.code(scene.view.index, 6) == "E2"
