from copy import deepcopy
from pathlib import Path
import pytest

from pyserato.builder import Crate, Builder
from pyserato.model.track import Track
from pyserato.util import DuplicateTrackError


@pytest.fixture
def child_crate1():
    child_crate1 = Crate("child1")
    return child_crate1


@pytest.fixture
def child_crate2(tmp_path):
    child_crate2 = Crate("child2")
    fake_path = Path("fake_data/song.mp3")
    child_crate2.add_track(Track.from_path(path=fake_path, user_root=tmp_path))
    return child_crate2


@pytest.fixture
def root_crate(child_crate1, child_crate2):
    root_crate = Crate("root", children=[child_crate1, child_crate2])
    return root_crate


def test_crate_crate(tmp_path, root_crate, child_crate1, child_crate2):
    assert root_crate.children == [child_crate1, child_crate2]
    assert set(map(lambda t: t.path, child_crate2.tracks)) == {tmp_path / Path("fake_data/song.mp3")}


def test_crate_equality(tmp_path, root_crate, child_crate1, child_crate2):
    duplicate_root_crate = Crate("root", children=[child_crate1, child_crate2])
    assert root_crate == duplicate_root_crate
    child_crate3 = Crate("child3")
    child_crate3.add_track(Track.from_path(Path("foo.mp3"), user_root=tmp_path))
    different_root_crate_with_extra_child = Crate("root", children=[child_crate1, child_crate2, child_crate3])
    assert root_crate != different_root_crate_with_extra_child
    different_root_crate_with_song_path = duplicate_root_crate
    different_root_crate_with_song_path.add_track(Track.from_path(Path("bar.mp3")))
    assert root_crate != different_root_crate_with_song_path


def test_crate_deepcopy(root_crate):
    new_root = deepcopy(root_crate)
    modified_child = new_root.children[0]
    modified_child.add_track(Track.from_path(path=Path("new_song.mp3")))
    assert modified_child != root_crate.children[0]
    assert root_crate != new_root


def test_crate_add(root_crate):
    child3 = Crate("child-3")
    child3.add_track(Track.from_path(path="child3/foo.mp3"))
    root_crate_2 = Crate("root", children=[child3])
    new_root = root_crate + root_crate_2
    assert new_root != root_crate
    assert new_root != root_crate_2
    assert len(new_root.children) == len(root_crate.children) + len(root_crate_2.children)
    for new_root_child, child in zip(new_root.children, root_crate.children + root_crate_2.children):
        assert new_root_child == child
    # now test that the children of the new_root are distinct copies
    new_root.children[0].add_track(Track.from_path(path=Path("new_song.mp3")))
    assert new_root.children[0].name == root_crate.children[0].name
    assert new_root.children[0] != root_crate.children[0]


def test_duplicate_tracks_error(tmp_path, root_crate):
    song_path = Path("fake_data/song.mp3")
    root_crate.add_track(Track.from_path(tmp_path / song_path))
    with pytest.raises(DuplicateTrackError):
        root_crate.add_track(Track.from_path(tmp_path / "fake_data/.." / song_path))


def test_crate_builder(tmp_path, root_crate, child_crate1, child_crate2):
    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    expected_crates = {"root": root_crate}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates


def test_crate_no_overwrite(tmp_path):
    child_crate1 = Crate("child1")
    root_crate = Crate("root", children=[child_crate1])
    root_crate.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    expected_crates = {"root": root_crate}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children=[child_crate2])
    child_crate2.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))
    builder.save(root_crate, subcrates_path.parent)
    expected_root = Crate("root", children=[child_crate1, child_crate2])
    # when the root crate was saved for the second time above we DID NOT set the overwrite flag. Therefore since the
    # path of the root crate already existed on disk, we do not expect the original root crate to be overwritten.
    # Therefore we expect the root to have its original songs still.
    expected_root.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))
    expected_crates = {"root": expected_root}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates


def test_crate_overwrite(tmp_path):
    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    child_crate1 = Crate("child1")
    root_crate = Crate("root", children=[child_crate1])
    root_crate.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)

    expected_crates = {"root": root_crate}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children=[child_crate2])
    child_crate2.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    builder.save(root_crate, subcrates_path.parent, overwrite=True)
    # when the root crate was saved for the second time above we DID set the overwrite flag. Therefore since the
    # path of the root crate already existed on disk, we do expect the original root crate to be overwritten.
    expected_crates = {"root": Crate("root", children=[child_crate1, child_crate2])}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates
