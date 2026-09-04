"""The Serato BeatGrid encoder.

The golden case is byte-exact: `_encode` must reproduce, bit for bit, the frame
Serato itself wrote into a real analysed file. That is the only assertion here
that proves the format was read correctly rather than merely read consistently,
so it comes first and is worth keeping even though it looks trivial.

The file-level tests run on a synthesized MP3 -- a handful of silent MPEG-1
Layer III frames, carrying the six GEOB frames Serato leaves on an analysed
track -- so they run on CI, where no Serato library exists. The two that need
Serato's own bytes rather than a plausible imitation still point at
~/Music/SubboxSeratoQA, which holds copies made for exactly this, and skip
without it -- never at ~/Music/_Serato_, and never at the fixtures in place:
every write here happens on a copy in a tmp_path.
"""
import shutil
import struct
from pathlib import Path

import pytest
from mutagen import id3
from mutagen.mp3 import MP3

from pyserato.encoders.beatgrid_mp3_encoder import BeatgridMp3Encoder
from pyserato.encoders.serato_tags import (
    SERATO_ANALYSIS,
    SERATO_BEATGRID,
    SERATO_MARKERS_V1,
    SERATO_MARKERS_V2,
    SERATO_OVERVIEW,
)
from pyserato.model.tempo import Tempo
from pyserato.model.track import Track

# n=1, position=0.045958050s, bpm=175.0 -- lifted from a real analysed file.
ZENITH = bytes.fromhex("0100000000013d3c3e82432f000000")
# Analysed, never gridded. A common state, and not an error.
UNGRIDDED = bytes.fromhex("01000000000000")

FIXTURES = Path("~/Music/SubboxSeratoQA").expanduser()
needs_fixtures = pytest.mark.skipif(
    not FIXTURES.is_dir(), reason="needs the analysed fixture library"
)
# What `needs_fixtures` guards cannot run on CI by design, so it is marked
# `no cover` as well -- otherwise its skipped body counts as untested code and
# drags the run's coverage under the floor on every machine but this one.


# One MPEG-1 Layer III frame: 128kbps, 44100Hz, no padding, silent payload.
# Enough for mutagen to find a sync word and treat the file as an MP3, which is
# all these tests need of the audio.
_MPEG_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413

# The frames Serato leaves on an analysed track, with stand-in payloads. Only
# their presence and their bytes staying untouched matter here; the sibling
# encoders own their contents.
_SIBLING_FRAMES = {
    SERATO_ANALYSIS: b"\x02\x01",
    "GEOB:Serato Autotags": b"\x01\x01175.00\x00",
    SERATO_OVERVIEW: b"\x01\x05" + bytes(range(16)),
    SERATO_MARKERS_V1: b"\x02\x05" + b"\x00" * 8,
    SERATO_MARKERS_V2: b"\x01\x01" + b"QVVUT1I=",
}


@pytest.fixture
def encoder():
    return BeatgridMp3Encoder()


@pytest.fixture
def analysed_mp3(tmp_path):
    """A synthetic stand-in for a Serato-analysed track: silent audio, six GEOB
    frames, a real one-marker grid among them."""
    path = tmp_path / "synthetic.mp3"
    path.write_bytes(_MPEG_FRAME * 20)
    tags = MP3(path)
    for name, data in _SIBLING_FRAMES.items():
        tags[name] = id3.GEOB(
            encoding=0,
            mime="application/octet-stream",
            desc=name.split(":", 1)[1],
            data=data,
        )
    tags[SERATO_BEATGRID] = id3.GEOB(
        encoding=0,
        mime="application/octet-stream",
        desc="Serato BeatGrid",
        data=ZENITH,
    )
    tags.save()
    return path


def _gridded_fixture():  # pragma: no cover -- QA machine only
    """An analysed fixture that actually carries a grid, or None."""
    for path in sorted(FIXTURES.rglob("*.mp3")):
        tag = MP3(path).get(SERATO_BEATGRID)
        if tag is not None and struct.unpack(">I", tag.data[2:6])[0] > 0:
            return path
    return None


def test_encode_reproduces_a_real_serato_frame_byte_for_byte(encoder):
    grid = [Tempo(position=0.04595804959535599, bpm=175.0)]
    assert encoder._encode(grid) == ZENITH


def test_decode_reads_that_frame_back(encoder):
    (marker,) = encoder._decode(ZENITH)
    assert marker.position == pytest.approx(0.045958, abs=1e-6)
    assert marker.bpm == 175.0
    assert marker.beats_till_next is None
    assert marker.terminal


def test_an_analysed_but_ungridded_track_decodes_to_an_empty_grid(encoder):
    # Distinct from "no frame", and just as much not an error.
    assert encoder._decode(UNGRIDDED) == []
    assert encoder._encode([]) == UNGRIDDED


def test_a_variable_tempo_grid_round_trips(encoder):
    # The multi-marker path: every anchor but the last carries a beat count.
    # NOTE: no fixture anywhere exercises this against real Serato output --
    # 30 gridded files on the QA machine all have n_markers of 0 or 1
    # (laker-93/pymix#153). This proves the encoder is self-consistent and that
    # it matches the documented layout; it does not prove Serato agrees. A
    # hand-gridded variable-tempo track is still needed.
    grid = [
        Tempo(position=0.5, beats_till_next=16),
        Tempo(position=8.0, beats_till_next=32),
        Tempo(position=21.5, bpm=142.5),
    ]
    payload = encoder._encode(grid)
    # 2 version + 4 count + 3 markers x 8 + 1 footer
    assert len(payload) == 31
    decoded = encoder._decode(payload)
    assert [m.beats_till_next for m in decoded] == [16, 32, None]
    assert [m.terminal for m in decoded] == [False, False, True]
    for original, read_back in zip(grid, decoded):
        assert read_back.position == pytest.approx(original.position, abs=1e-5)
    assert decoded[-1].bpm == pytest.approx(142.5, abs=1e-3)


def test_the_marker_shapes_are_one_byte_width_apart(encoder):
    # Why _encode is strict: a non-terminal marker's uint32 beat count and a
    # terminal marker's float32 bpm occupy the same four bytes. Nothing
    # downstream can tell a mis-shaped grid from a real one, so it is refused
    # at the point of writing rather than written as a plausible wrong answer.
    terminal = encoder._encode([Tempo(position=1.0, bpm=128.0)])
    assert len(terminal) == len(encoder._encode([
        Tempo(position=1.0, beats_till_next=4), Tempo(position=2.0, bpm=128.0),
    ])) - 8


@pytest.mark.parametrize("grid, match", [
    ([Tempo(position=1.0)], "must carry a bpm"),
    ([Tempo(position=1.0, beats_till_next=4)], "must carry a bpm"),
    ([Tempo(position=1.0, bpm=128.0), Tempo(position=2.0, bpm=130.0)],
     "must carry beats_till_next"),
    ([Tempo(bpm=128.0)], "no position"),
])
def test_encode_refuses_a_grid_it_cannot_represent(encoder, grid, match):
    with pytest.raises(ValueError, match=match):
        encoder._encode(grid)


def test_decode_refuses_the_wrong_version(encoder):
    # (1, 1) is Markers2. Reading it as a grid would yield plausible garbage.
    with pytest.raises(AssertionError, match="version"):
        encoder._decode(b"\x01\x01" + b"\x00\x00\x00\x00" + b"\x00")


def test_decode_refuses_a_truncated_grid(encoder):
    with pytest.raises(ValueError, match="ran out"):
        encoder._decode(b"\x01\x00" + struct.pack(">I", 3) + b"\x00" * 8)


def test_bpm_between_derives_the_tempo_serato_infers(encoder):
    # 16 beats in 7.5 seconds is 128 BPM.
    first = Tempo(position=0.5, beats_till_next=16)
    second = Tempo(position=8.0, bpm=140.0)
    assert encoder.bpm_between(first, second) == pytest.approx(128.0)

    with pytest.raises(ValueError, match="stored, not derived"):
        encoder.bpm_between(second, second)
    with pytest.raises(ValueError, match="strictly increasing"):
        encoder.bpm_between(first, Tempo(position=0.5, bpm=140.0))
    with pytest.raises(ValueError, match="must have a position"):
        encoder.bpm_between(first, Tempo(bpm=140.0))


def test_reading_a_track_with_no_frame_gives_an_empty_grid(encoder, analysed_mp3):
    tags = MP3(analysed_mp3)
    tags.pop(SERATO_BEATGRID, None)
    tags.save()

    assert encoder.read_beatgrid(Track(path=analysed_mp3)) == []


def test_reading_an_unreadable_frame_gives_an_empty_grid_rather_than_raising(
    encoder, analysed_mp3
):
    track = Track(path=analysed_mp3)
    encoder._write(track, b"\x09\x09nonsense").save()

    assert encoder.read_beatgrid(track) == []


def test_a_written_grid_reads_back_off_disk(encoder, analysed_mp3):
    track = Track(path=analysed_mp3)
    track.add_beatgrid_marker(Tempo(position=0.5, beats_till_next=16))
    track.add_beatgrid_marker(Tempo(position=8.0, bpm=128.0))
    encoder.write(track)

    first, second = encoder.read_beatgrid(track)
    assert first.beats_till_next == 16
    assert first.position == pytest.approx(0.5)
    assert second.terminal and second.bpm == pytest.approx(128.0)


@needs_fixtures
def test_a_real_analysed_files_grid_reads_back(encoder):  # pragma: no cover
    source = _gridded_fixture()
    if source is None:
        pytest.skip("no gridded fixture")
    grid = encoder.read_beatgrid(Track(path=source))
    assert len(grid) >= 1
    assert grid[-1].terminal and grid[-1].bpm > 0
    assert all(m.position is not None for m in grid)


def test_writing_a_grid_leaves_every_sibling_geob_frame_alone(encoder, analysed_mp3):
    # The damage that cannot be undone: Analysis, Autotags, Overview, Markers_
    # and Markers2 are minutes of analysis plus any manual gridding, and
    # assigning the whole GEOB array takes all of them (laker-93/pyserato#9).
    _assert_only_the_grid_frame_changed(encoder, analysed_mp3)


@needs_fixtures
def test_a_real_analysed_file_keeps_its_sibling_frames_too(  # pragma: no cover
    encoder, tmp_path
):
    # The same assertion against Serato's own six frames rather than our
    # stand-ins, in case a real payload trips something the synthetic one does
    # not. Skips off the QA machine.
    source = _gridded_fixture() or next(iter(sorted(FIXTURES.rglob("*.mp3"))), None)
    if source is None:
        pytest.skip("no fixture mp3s")
    copy = tmp_path / source.name
    shutil.copy(source, copy)
    _assert_only_the_grid_frame_changed(encoder, copy)


def _assert_only_the_grid_frame_changed(encoder, copy):
    before = {k: v.data for k, v in MP3(copy).items() if k.startswith("GEOB:")}
    assert len(before) > 1, "fixture must carry sibling frames for this to mean anything"

    track = Track(path=copy)
    track.add_beatgrid_marker(Tempo(position=1.25, bpm=128.0))
    encoder.write(track)

    after = {k: v.data for k, v in MP3(copy).items() if k.startswith("GEOB:")}
    assert set(after) == set(before)
    for name, data in before.items():
        if name != SERATO_BEATGRID:
            assert after[name] == data, f"{name} was modified"

    (marker,) = encoder.read_beatgrid(track)
    assert marker.bpm == 128.0
    assert marker.position == pytest.approx(1.25, abs=1e-5)
