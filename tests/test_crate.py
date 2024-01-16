from pathlib import Path
import pytest

from pyserato import util
from pyserato.crate import Crate, Builder
from pyserato.util import DuplicateTrackError


def _create_encoded_playlist_section(song_paths: list[Path]) -> bytes:
    """
    Unfortunately, forced to use the code under test within the tests itself since we must dynamically set the buffer
    to the path that is being used by the test. We cannot use a fixed fake data path as the full path is encoded in the
    crate buffer and this full path will change depending on where the test is being run.
    :param song_paths:
    :return:
    """
    playlist_section = bytes()
    for song_path in song_paths:
        absolute_song_path = Path(song_path).resolve()
        data = util.to_serato_string(str(absolute_song_path))
        ptrk_size = util.int_to_hexbin(len(data))
        otrk_size = util.int_to_hexbin(len(data) + 8)
        playlist_section += "otrk".encode()
        playlist_section += otrk_size
        playlist_section += "ptrk".encode()
        playlist_section += ptrk_size
        playlist_section += data.encode()
    return playlist_section


@pytest.fixture
def child_crate1():
    child_crate1 = Crate("child1")
    return child_crate1


@pytest.fixture
def child_crate2(tmp_path):
    child_crate2 = Crate("child2")
    fake_path = Path("fake_data/song.mp3")
    child_crate2.add_song(fake_path, user_root=tmp_path)
    return child_crate2


@pytest.fixture
def root_crate(child_crate1, child_crate2):
    root_crate = Crate("root", children=[child_crate1, child_crate2])
    return root_crate


def test_create_crate(tmp_path, root_crate, child_crate1, child_crate2):
    assert root_crate.children == [child_crate1, child_crate2]
    assert child_crate2.song_paths == {tmp_path / Path("fake_data/song.mp3")}


def test_duplicate_tracks_error(tmp_path, root_crate):
    song_path = Path("fake_data/song.mp3")
    root_crate.add_song(tmp_path / song_path)
    with pytest.raises(DuplicateTrackError):
        root_crate.add_song(tmp_path / "fake_data/.." / song_path)


def test_crate_builder(tmp_path, root_crate, child_crate1, child_crate2):
    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    crate_names_to_content = {}
    expected_crate_names_content = {
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root%%child2.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a"
        b"\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t\x00c\x00h"
        b"\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    expected_crate_names_content["root%%child2.crate"] += _create_encoded_playlist_section(
        list(child_crate2.song_paths)
    )
    for f in subcrates_path.iterdir():
        crate_name = f.name
        crate_content = f.read_bytes()
        crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content


def test_crate_no_overwrite(tmp_path):
    child_crate1 = Crate("child1")
    root_crate = Crate("root", children=[child_crate1])
    root_crate.add_song(Path("foo/bar.mp3"), user_root=tmp_path)

    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    crate_names_to_content = {}
    expected_crate_names_content = {
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a"
        b"\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t\x00c\x00h"
        b"\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c"
        b"\x00r\x00a\x00t\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    expected_crate_names_content["root.crate"] += _create_encoded_playlist_section(list(root_crate.song_paths))

    for f in subcrates_path.iterdir():
        if f.is_file():
            crate_name = f.name
            crate_content = f.read_bytes()
            crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children=[child_crate2])
    child_crate2.add_song(Path("foo/bar.mp3"), user_root=tmp_path)

    builder.save(root_crate, subcrates_path.parent)
    crate_names_to_content = {}
    expected_crate_names_content = {
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root%%child2.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a"
        b"\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t\x00c\x00h"
        b"\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    expected_crate_names_content["root%%child2.crate"] += _create_encoded_playlist_section(
        list(child_crate2.song_paths)
    )
    expected_crate_names_content["root.crate"] += _create_encoded_playlist_section(list(child_crate2.song_paths))

    for f in subcrates_path.iterdir():
        if f.is_file():
            crate_name = f.name
            crate_content = f.read_bytes()
            crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content


def test_crate_overwrite(tmp_path):
    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    child_crate1 = Crate("child1")
    root_crate = Crate("root", children=[child_crate1])
    root_crate.add_song(Path("foo/bar.mp3"), user_root=tmp_path)

    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    crate_names_to_content = {}
    expected_crate_names_content = {
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a"
        b"\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t\x00c\x00h"
        b"\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c"
        b"\x00r\x00a\x00t\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    expected_crate_names_content["root.crate"] += _create_encoded_playlist_section(list(root_crate.song_paths))

    for f in subcrates_path.iterdir():
        if f.is_file():
            crate_name = f.name
            crate_content = f.read_bytes()
            crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children=[child_crate2])
    child_crate2.add_song(Path("foo/bar.mp3"), user_root=tmp_path)

    builder.save(root_crate, subcrates_path.parent, overwrite=True)
    crate_names_to_content = {}

    # here the contents of the root crate have been overwritten
    expected_crate_names_content = {
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root%%child2.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a"
        b"\x00t\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    expected_crate_names_content["root%%child2.crate"] += _create_encoded_playlist_section(
        list(child_crate2.song_paths)
    )

    for f in subcrates_path.iterdir():
        if f.is_file():
            crate_name = f.name
            crate_content = f.read_bytes()
            crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content


def test_build_crate_from_filepath(tmp_path):
    builder = Builder()
    crates_to_content = {
        "root%%child1.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root%%child2.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e"
        b"\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t"
        b"\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a"
        b"\x00t\x00e",
        "root.crate": b"vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a"
        b"\x00t\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e",
    }
    song_path = tmp_path / "foo" / "bar.mp3"
    crates_to_content["root%%child2.crate"] += _create_encoded_playlist_section([song_path])

    child2 = Crate("child2")
    child2.add_song(song_path)
    expected_crates = [
        Crate("root", children=[Crate("child1")]),
        Crate("root", children=[child2]),
        Crate("root"),
    ]
    for i, (crate_name, contents) in enumerate(crates_to_content.items()):
        path = tmp_path / Path(crate_name)
        path.write_bytes(contents)
        crate = builder.build_crates_from_filepath(path)
        expected_crate = expected_crates[i]
        assert crate.name == expected_crate.name
        assert crate.song_paths == expected_crate.song_paths
        if crate.children:
            assert crate.children[0].name == expected_crate.children[0].name
            assert crate.children[0].song_paths == expected_crate.children[0].song_paths
