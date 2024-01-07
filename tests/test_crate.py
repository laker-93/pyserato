from pathlib import Path
import pytest
from pyserato.crate import Crate, Builder


@pytest.fixture
def child_crate1():
    child_crate1 = Crate('child1')
    return child_crate1


@pytest.fixture
def child_crate2():
    child_crate2 = Crate('child2')
    fake_path = "/foo/bar/song.mp3"
    child_crate2.add_song(fake_path, user_root='/User/test')
    return child_crate2


@pytest.fixture
def root_crate(child_crate1, child_crate2):
    root_crate = Crate('root', children=[child_crate1, child_crate2])
    return root_crate


def test_create_crate(root_crate, child_crate1, child_crate2):
    assert root_crate.children == [child_crate1, child_crate2]
    assert child_crate2.song_paths == [Path("/User/test/foo/bar/song.mp3")]


def test_crate_builder(root_crate, child_crate1, child_crate2, tmp_path):
    # must make the directory where the crates will be written
    crate_path = tmp_path / 'SubCrates'
    crate_path.mkdir()

    builder = Builder()
    builder.save(root_crate, tmp_path)
    crate_names_to_content = {}
    expected_crate_names_content = {'root%%child1.crate': b'vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e'
                                                          b'\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t'
                                                          b'\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a'
                                                          b'\x00t\x00e',
                                    'root%%child2.crate': b'vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e'
                                                          b'\x00r\x00a\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t'
                                                          b'\x00c\x00h\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a'
                                                          b'\x00t\x00eotrk\x00\x00\x00>ptrk\x00\x00\x006\x00/\x00U'
                                                          b'\x00s\x00e\x00r\x00/\x00t\x00e\x00s\x00t\x00/\x00f'
                                                          b'\x00o\x00o\x00/\x00b\x00a\x00r\x00/\x00s\x00o\x00n'
                                                          b'\x00g\x00.\x00m\x00p\x003',
                                    'root.crate': b'vrsn\x00\x00\x008\x001\x00.\x000\x00/\x00S\x00e\x00r\x00a'
                                                  b'\x00t\x00o\x00\x00\x00S\x00c\x00r\x00a\x00t\x00c\x00h'
                                                  b'\x00L\x00i\x00v\x00e\x00\x00\x00C\x00r\x00a\x00t\x00e'}
    for f in crate_path.iterdir():
        crate_name = f.name
        crate_content = f.read_bytes()
        crate_names_to_content[crate_name] = crate_content

    assert expected_crate_names_content == crate_names_to_content
