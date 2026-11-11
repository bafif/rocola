from __future__ import annotations

import pytest

from rocola.mpdclient import MPDClient, MPDError, _esc


def connect(fake_mpd, responses=None, **kwargs) -> tuple[MPDClient, object]:
    srv = fake_mpd(responses, **kwargs)
    client = MPDClient("127.0.0.1", srv.port, timeout=2.0)
    client.connect()
    return client, srv


def test_connect_and_close(fake_mpd):
    client, _ = connect(fake_mpd)
    assert client.connected
    client.close()
    assert not client.connected


def test_unexpected_greeting_is_rejected(fake_mpd):
    srv = fake_mpd(greeting="HELLO")
    client = MPDClient("127.0.0.1", srv.port, timeout=2.0)
    with pytest.raises(MPDError):
        client.connect()
    assert not client.connected


def test_send_without_connection_raises():
    with pytest.raises(MPDError):
        MPDClient().status()


def test_status_is_parsed_into_a_dict(fake_mpd):
    client, _ = connect(fake_mpd, {"status": ["volume: 40", "state: play", "song: 3"]})
    assert client.status() == {"volume": "40", "state": "play", "song": "3"}


def test_values_may_contain_colon_space(fake_mpd):
    client, _ = connect(fake_mpd, {"currentsong": ["file: a.mp3", "Title: Intro: Part 1"]})
    assert client.current_song()["Title"] == "Intro: Part 1"


def test_ack_raises(fake_mpd):
    client, _ = connect(fake_mpd, {"play 99": "ACK [2@0] {play} Bad song index"})
    with pytest.raises(MPDError, match="Bad song index"):
        client.play(99)


def test_volume_is_clamped(fake_mpd):
    client, srv = connect(fake_mpd)
    client.set_volume(150)
    client.set_volume(-5)
    assert srv.commands[-2:] == ["setvol 100", "setvol 0"]


def test_change_volume_uses_current_volume(fake_mpd):
    client, srv = connect(fake_mpd, {"status": ["volume: 95"]})
    client.change_volume(10)
    assert srv.commands[-1] == "setvol 100"


def test_change_volume_without_mixer_falls_back(fake_mpd):
    # MPD reports volume: -1 (or omits it) when there is no mixer.
    client, srv = connect(fake_mpd, {"status": ["state: stop"]})
    client.change_volume(-10)
    assert srv.commands[-1] == "setvol 40"


def test_list_artists_and_albums(fake_mpd):
    client, srv = connect(
        fake_mpd,
        {
            "list artist": ["Artist: A", "Artist: B"],
            'list album artist "A"': ["Album: First"],
        },
    )
    assert client.list_artists() == ["A", "B"]
    assert client.list_albums("A") == ["First"]


def test_find_album_groups_objects_by_file(fake_mpd):
    client, _ = connect(
        fake_mpd,
        {
            'find album "X"': [
                "file: x/1.mp3",
                "Title: One",
                "file: x/2.mp3",
                "Title: Two",
            ]
        },
    )
    assert client.find_album("X") == [
        {"file": "x/1.mp3", "Title": "One"},
        {"file": "x/2.mp3", "Title": "Two"},
    ]


def test_all_files_skips_directories(fake_mpd):
    client, _ = connect(
        fake_mpd,
        {
            "listallinfo": [
                "directory: x",
                "file: x/1.mp3",
                "Title: One",
            ]
        },
    )
    assert client.all_files() == [{"file": "x/1.mp3", "Title": "One"}]


def test_play_uri_escapes_quotes(fake_mpd):
    client, srv = connect(fake_mpd)
    client.play_uri('rock/"live".mp3')
    assert srv.commands[0] == 'addid "rock/\\"live\\".mp3"'


@pytest.mark.parametrize("state", ["stop", "pause"])
def test_play_uri_starts_the_new_song_when_not_playing(fake_mpd, state):
    # Stopped after the queue ran out, a bare `play` restarts the queue from its
    # first song; paused, it resumes the old one. The chosen song is played by id.
    client, srv = connect(
        fake_mpd, {'addid "b.mp3"': ["Id: 7"], "status": [f"state: {state}", "song: 0"]}
    )
    client.play_uri("b.mp3")
    assert srv.commands == ['addid "b.mp3"', "status", "playid 7"]


def test_play_uri_only_queues_while_another_song_plays(fake_mpd):
    client, srv = connect(fake_mpd, {'addid "b.mp3"': ["Id: 7"], "status": ["state: play"]})
    client.play_uri("b.mp3")
    assert srv.commands == ['addid "b.mp3"', "status"]


def test_esc():
    assert _esc('a"b\\c') == 'a\\"b\\\\c'


def test_stats(fake_mpd):
    client, _ = connect(fake_mpd, {"stats": ["songs: 2", "db_update: 1730000000"]})
    assert client.stats()["db_update"] == "1730000000"


def test_an_ack_keeps_the_connection(fake_mpd):
    client, _ = connect(fake_mpd, {"play 99": "ACK [2@0] {play} Bad song index"})
    with pytest.raises(MPDError):
        client.play(99)
    assert client.connected


def test_a_cut_answer_closes_the_connection(fake_mpd):
    # An answer that never ends (no OK): the read times out. The rest of it could still
    # arrive later and be taken as the reply to the next command, so the client drops
    # the connection instead of reusing it.
    srv = fake_mpd({"listallinfo": b"file: a.mp3\nTitle: A\n"})
    client = MPDClient("127.0.0.1", srv.port, timeout=0.3)
    client.connect()
    with pytest.raises(OSError):
        client.all_files()
    assert not client.connected


def test_song_at_a_place_in_the_queue(fake_mpd):
    replies = {
        "playlistinfo 1": ["file: b.mp3", "Title: Dos", "Pos: 1"],
        "playlistinfo 7": "ACK [2@0] {playlistinfo} Bad song index",
    }
    client, srv = connect(fake_mpd, replies)
    assert client.song_at(1) == {"file": "b.mp3", "Title": "Dos", "Pos": "1"}
    assert client.song_at(7) == {}  # past the end of the queue (it changed meanwhile)
    assert client.connected
    assert srv.commands[-2:] == ["playlistinfo 1", "playlistinfo 7"]
