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
    children = [child_crate1, child_crate2]
    root_crate = Crate("root", children={c.name: c for c in children})
    return root_crate


def test_crate_crate(tmp_path, root_crate, child_crate1, child_crate2):
    assert root_crate.children == {c.name: c for c in [child_crate1, child_crate2]}
    assert set(map(lambda t: t.path, child_crate2.tracks)) == {tmp_path / Path("fake_data/song.mp3")}


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
    root_crate = Crate("root", children={c.name: c for c in [child_crate1]})
    root_crate.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    subcrates_path = tmp_path / "SubCrates"
    subcrates_path.mkdir()
    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)
    expected_crates = {"root": root_crate}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children={c.name: c for c in [child_crate2]})
    child_crate2.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))
    builder.save(root_crate, subcrates_path.parent)
    expected_root = Crate("root", children={c.name: c for c in [child_crate1, child_crate2]})
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
    root_crate = Crate("root", children={c.name: c for c in [child_crate1]})
    root_crate.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    builder = Builder()
    builder.save(root_crate, subcrates_path.parent)

    expected_crates = {"root": root_crate}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates

    child_crate2 = Crate("child2")
    root_crate = Crate("root", children={c.name: c for c in [child_crate2]})
    child_crate2.add_track(Track.from_path(Path("foo/bar.mp3"), user_root=tmp_path))

    builder.save(root_crate, subcrates_path.parent, overwrite=True)
    # when the root crate was saved for the second time above we DID set the overwrite flag. Therefore since the
    # path of the root crate already existed on disk, we do expect the original root crate to be overwritten.
    expected_crates = {"root": Crate("root", children={c.name: c for c in [child_crate1, child_crate2]})}
    actual_crates = builder.parse_crates_from_root_path(subcrates_path)
    assert actual_crates == expected_crates
