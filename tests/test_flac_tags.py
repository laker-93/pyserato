"""Serato tags in a FLAC, and the container dispatch that finds them.

The payload format is not retested here -- it is container-independent, and
test_beatgrid.py and test_hot_cue.py own it. What is tested is everything
around it: which reader a file gets, the base64 envelope a Vorbis comment wraps
the payload in, and the parts of the user's file a write must not touch.

Two kinds of evidence, deliberately kept apart:

* `analysed.flac` and `analysed.mp3` carry real Serato payloads. The tests over
  them assert the two containers give the same reading, which is the property
  subbox depends on -- the client writes cues with tserato and the server reads
  them back with pyserato.
* The synthetic files from `builders.py` have never been near Serato. They exist
  so the write tests have a file whose every other tag and metadata block is
  known, and can be asserted untouched afterwards.

Every write happens on a copy in tmp_path. The fixtures are never written to.
"""

import base64
import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC
from mutagen.mp3 import MP3

from builders import flac_bytes, id3_prefixed, mp3_bytes, write_flac
from pyserato.encoders.beatgrid_encoder import BeatgridEncoder
from pyserato.encoders.io import (
    FlacTagIO,
    Mp3TagIO,
    UnsupportedContainerError,
    probe_container,
    tag_io_for,
)
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.tempo import Tempo
from pyserato.model.track import Track
from pyserato.encoders.v2_encoder import V2Encoder

FIXTURES = Path(__file__).parent / "fixtures"
MARKERS2 = "Serato Markers2"
BEATGRID = "Serato BeatGrid"

# The envelope prefix recorded off a *real* Serato-analysed FLAC in
# laker-93/pyserato#12. Everything this module writes must reproduce it exactly:
# mime, an empty filename, the tag's description, and only then the payload.
REAL_MARKERS2_PREFIX = b"application/octet-stream\x00\x00Serato Markers2\x00"


@pytest.fixture
def copied():
    """A fixture file copied into tmp_path, because writes happen to it."""
    def _copy(name: str, tmp_path: Path) -> Path:
        target = tmp_path / name
        shutil.copy(FIXTURES / name, target)
        return target
    return _copy


# --------------------------------------------------------------------------
# Which reader a file gets
# --------------------------------------------------------------------------

@pytest.mark.parametrize("head, expected", [
    (b"fLaC" + b"\x00" * 32, "FLAC"),
    (b"ID3\x04\x00\x00\x00\x00\x00\x0a" + b"\x00" * 32, "MP3"),
    (b"RIFF....WAVE" + b"\x00" * 20, "WAV"),
    (b"FORM....AIFF" + b"\x00" * 20, "AIFF"),
    (b"OggS" + b"\x00" * 32, "Ogg"),
    (b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 20, "M4A"),
    # Neither a frame sync nor an ID3 tag. Falls to MP3, which is where it went
    # before the probe existed: refusing it would break reads that work today.
    (b"junk junk junk junk junk", "MP3"),
])
def test_the_container_comes_from_the_bytes(tmp_path, head, expected):
    path = tmp_path / "whatever.mp3"
    path.write_bytes(head)
    assert probe_container(path) == expected


def test_a_flac_named_mp3_is_still_a_flac(tmp_path):
    # The case this whole seam exists for: dispatching on the extension would
    # hand this to the MP3 reader, which answers "no cues" rather than failing.
    path = tmp_path / "download.mp3"
    path.write_bytes(flac_bytes(["ARTIST=A"]))
    assert probe_container(path) == "FLAC"
    assert isinstance(tag_io_for(path), FlacTagIO)


def test_a_flac_behind_an_id3_tag_is_still_a_flac(tmp_path):
    path = tmp_path / "tagged.flac"
    path.write_bytes(id3_prefixed(flac_bytes(["ARTIST=A"])))
    assert probe_container(path) == "FLAC"


def test_an_id3_prefixed_flac_round_trips_with_its_id3_tag_intact(tmp_path):
    # mutagen finds the FLAC stream behind the tag and puts the tag back, which
    # is why FlacTagIO carries no offset. If that ever stops being true, the
    # leading tag is what disappears.
    flac = flac_bytes(["ARTIST=A"])
    original = id3_prefixed(flac)
    id3_tag = original[:len(original) - len(flac)]
    path = tmp_path / "tagged.flac"
    path.write_bytes(original)

    tag_io_for(path).write(MARKERS2, b"\x01\x01payload")

    assert path.read_bytes().startswith(id3_tag)
    assert tag_io_for(path).read(MARKERS2) == b"\x01\x01payload"


def test_an_mp3_gets_the_mp3_reader(tmp_path):
    path = tmp_path / "track.mp3"
    path.write_bytes(mp3_bytes())
    assert isinstance(tag_io_for(path), Mp3TagIO)


@pytest.mark.parametrize("head, container", [
    (b"RIFF....WAVE" + b"\x00" * 20, "WAV"),
    (b"FORM....AIFF" + b"\x00" * 20, "AIFF"),
    (b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 20, "M4A"),
    (b"OggS" + b"\x00" * 32, "Ogg"),
])
def test_a_container_with_no_reader_is_refused_by_name(tmp_path, head, container):
    # By name, and not as a generic failure: "not implemented yet" is routine in
    # a real library and "this file is broken" is worth a warning, and a caller
    # can only tell them apart if the exception says which it is.
    path = tmp_path / "track.dat"
    path.write_bytes(head)
    with pytest.raises(UnsupportedContainerError) as raised:
        tag_io_for(path)
    assert raised.value.container == container
    assert container in str(raised.value)


# --------------------------------------------------------------------------
# Reading real Serato bytes out of a FLAC
# --------------------------------------------------------------------------

def test_the_flac_and_the_mp3_of_one_track_give_the_same_cues():
    # The property subbox actually depends on. Same track, same Serato payload,
    # two containers -- and in the real flow one of them was written by tserato
    # and read here.
    encoder = V2Encoder()
    from_mp3 = encoder.read_cues(Track.from_path(FIXTURES / "analysed.mp3"))
    from_flac = encoder.read_cues(Track.from_path(FIXTURES / "analysed.flac"))

    assert len(from_flac) == 4
    assert [(c.type, c.index, c.name, c.start, c.end) for c in from_flac] == \
           [(c.type, c.index, c.name, c.start, c.end) for c in from_mp3]


def test_the_flac_payload_is_byte_identical_to_the_mp3s():
    mp3 = Mp3TagIO(FIXTURES / "analysed.mp3").read(MARKERS2)
    flac = FlacTagIO(FIXTURES / "analysed.flac").read(MARKERS2)
    assert flac == mp3


def test_an_analysed_but_ungridded_flac_reads_as_an_empty_grid():
    # The fixture carries a real beatgrid tag with zero markers. Not an error,
    # and not the same as having no tag.
    assert FlacTagIO(FIXTURES / "analysed.flac").read(BEATGRID) is not None
    assert BeatgridEncoder().read_beatgrid(Track.from_path(FIXTURES / "analysed.flac")) == []


def test_a_tag_the_file_does_not_carry_reads_as_none(tmp_path):
    path = write_flac(tmp_path / "plain.flac", ["ARTIST=A"])
    assert FlacTagIO(path).read(MARKERS2) is None


def test_a_flac_with_no_comment_block_at_all_reads_as_none(tmp_path):
    # mutagen reports `tags` as None rather than empty for this, so it is a
    # separate path from "has comments, none of them Serato's".
    path = write_flac(tmp_path / "bare.flac", comments=None)
    assert FLAC(path).tags is None
    assert FlacTagIO(path).read(MARKERS2) is None


def test_cues_read_as_empty_rather_than_raising_when_there_is_no_tag(tmp_path):
    # laker-93/pyserato#8: this used to be a KeyError every caller had to know
    # to catch, on the most ordinary file there is -- one Serato never analysed.
    flac = write_flac(tmp_path / "plain.flac", ["ARTIST=A"])
    mp3 = tmp_path / "plain.mp3"
    mp3.write_bytes(mp3_bytes())

    assert V2Encoder().read_cues(Track.from_path(flac)) == []
    assert V2Encoder().read_cues(Track.from_path(mp3)) == []


@pytest.mark.parametrize("mangle", [
    lambda b64: b64,                                    # as Serato writes it
    lambda b64: b64 + "=" * (-len(b64) % 4),            # padded
    lambda b64: b64.replace("\n", ""),                  # unwrapped
])
def test_the_base64_is_read_however_it_is_spelled(tmp_path, mangle):
    payload = b"\x01\x01some payload"
    raw = base64.b64encode(REAL_MARKERS2_PREFIX + payload).decode().rstrip("=")
    wrapped = "\n".join(raw[i:i + 72] for i in range(0, len(raw), 72))
    path = write_flac(tmp_path / "x.flac", [f"serato_markers_v2={mangle(wrapped)}"])
    assert FlacTagIO(path).read(MARKERS2) == payload


def test_a_comment_holding_a_different_tag_is_refused(tmp_path):
    # A Markers2 payload handed to the beatgrid decoder does not fail -- it
    # reads as a grid with an absurd number of markers -- so this has to be
    # caught where the envelope still says which tag it is.
    envelope = b"application/octet-stream\x00\x00Serato Overview\x00payload"
    path = write_flac(
        tmp_path / "x.flac",
        [f"serato_markers_v2={base64.b64encode(envelope).decode()}"],
    )
    with pytest.raises(ValueError, match="Serato Overview"):
        FlacTagIO(path).read(MARKERS2)


def test_a_comment_that_is_not_an_envelope_at_all_is_refused(tmp_path):
    path = write_flac(
        tmp_path / "x.flac",
        [f"serato_markers_v2={base64.b64encode(b'no nulls here').decode()}"],
    )
    with pytest.raises(ValueError, match="not a Serato envelope"):
        FlacTagIO(path).read(MARKERS2)


def test_a_serato_tag_with_no_known_flac_field_is_refused(tmp_path):
    # Markers_ and Autotags have no published FLAC field name. Guessing one
    # would write a comment Serato never reads and no tool cleans up.
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    with pytest.raises(ValueError, match="Serato Markers_"):
        FlacTagIO(path).read("Serato Markers_")


# --------------------------------------------------------------------------
# Writing, and what a write must not touch
# --------------------------------------------------------------------------

def test_a_payload_round_trips(tmp_path):
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    payload = bytes(range(256))
    FlacTagIO(path).write(MARKERS2, payload)
    assert FlacTagIO(path).read(MARKERS2) == payload


def test_the_written_comment_looks_like_seratos_own(tmp_path):
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")

    (value,) = [v for k, v in FLAC(path).tags if k == "serato_markers_v2"]
    assert "=" not in value, "Serato writes the base64 unpadded"
    assert all(len(line) <= 72 for line in value.split("\n")), "wrapped at 72"
    decoded = base64.b64decode("".join(value.split()) + "==")
    assert decoded.startswith(REAL_MARKERS2_PREFIX)
    assert len(REAL_MARKERS2_PREFIX) == 42


def test_writing_keeps_the_spelling_the_file_already_uses(tmp_path):
    # Vorbis field names are case-insensitive per the spec, so writing a
    # different case leaves two comments with no defined precedence -- and
    # `tags[field] = value` in mutagen does exactly that, as well as moving the
    # comment to the end of the list.
    path = write_flac(tmp_path / "x.flac", ["SERATO_MARKERS_V2=QUJD", "ARTIST=A"])
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")

    keys = [k for k, _ in FLAC(path).tags]
    assert keys == ["SERATO_MARKERS_V2", "ARTIST"]


def test_a_write_leaves_every_other_comment_alone(tmp_path):
    before = ["ARTIST=Basalt Bloom", "TITLE=Zenith Lantern", "ARTIST=Second Artist",
              "COMMENT=see https://example.test/?a=1&b=2"]
    path = write_flac(tmp_path / "x.flac", before)
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")

    kept = [f"{k}={v}" for k, v in FLAC(path).tags if not k.lower().startswith("serato_")]
    # Order, repetition, case and the '=' inside a value: all of it survives.
    assert kept == before


def test_a_write_leaves_every_other_metadata_block_alone(tmp_path, copied):
    path = copied("analysed.flac", tmp_path)
    before = FLAC(path)
    FlacTagIO(path).write(BEATGRID, b"\x01\x00\x00\x00\x00\x00\x00")
    after = FLAC(path)

    # Seektable and application survive, and so does the audio: same md5, same
    # sample count. A writer that rebuilds the block list drops the first two.
    assert sorted(b.code for b in after.metadata_blocks) == \
           sorted(b.code for b in before.metadata_blocks)
    assert after.info.md5_signature == before.info.md5_signature
    assert after.info.total_samples == before.info.total_samples
    assert FlacTagIO(path).read(MARKERS2) == FlacTagIO(FIXTURES / "analysed.flac").read(MARKERS2)


def test_writing_the_same_payload_twice_changes_nothing(tmp_path):
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")
    once = path.read_bytes()
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")
    assert path.read_bytes() == once


def test_a_flac_with_no_comment_block_gains_one(tmp_path):
    path = write_flac(tmp_path / "bare.flac", comments=None)
    FlacTagIO(path).write(MARKERS2, b"\x01\x01payload")
    assert FlacTagIO(path).read(MARKERS2) == b"\x01\x01payload"


# --------------------------------------------------------------------------
# The encoders, through a FLAC
# --------------------------------------------------------------------------

def test_cues_round_trip_through_a_flac(tmp_path):
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    track = Track.from_path(path)
    track.add_hot_cue(HotCue(name="drop", type=HotCueType.CUE, start=1000, index=0))
    track.add_hot_cue(HotCue(name="tail", type=HotCueType.LOOP, start=20000, end=24000, index=0))

    V2Encoder().write(track)

    read_back = V2Encoder().read_cues(Track.from_path(path))
    assert [(c.name, c.start, c.end, c.type) for c in read_back] == [
        ("drop", 1000, None, HotCueType.CUE),
        ("tail", 20000, 24000, HotCueType.LOOP),
    ]


def test_a_beatgrid_round_trips_through_a_flac(tmp_path):
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    track = Track.from_path(path)
    track.add_beatgrid_marker(Tempo(position=0.045958, bpm=175.0))

    BeatgridEncoder().write(track)

    (marker,) = BeatgridEncoder().read_beatgrid(Track.from_path(path))
    assert marker.position == pytest.approx(0.045958, abs=1e-6)
    assert marker.bpm == 175.0


def test_a_flacs_existing_footer_byte_is_carried_not_guessed(tmp_path):
    # The byte after the markers is the one field in the format nobody can read.
    # The rule for it is the rule for the sibling tags: do not overwrite what
    # you cannot reproduce.
    path = write_flac(tmp_path / "x.flac", ["ARTIST=A"])
    FlacTagIO(path).write(BEATGRID, b"\x01\x00\x00\x00\x00\x00\x2a")
    assert BeatgridEncoder().read_footer(Track.from_path(path)) == b"\x2a"

    track = Track.from_path(path)
    track.add_beatgrid_marker(Tempo(position=1.0, bpm=128.0))
    BeatgridEncoder().write(track)

    assert FlacTagIO(path).read(BEATGRID)[-1:] == b"\x2a"


def test_an_unsupported_container_reaches_the_caller_as_itself(tmp_path):
    # read_beatgrid turns anything it cannot parse into an empty grid, which is
    # right for a corrupt tag and wrong for a format nobody has written a reader
    # for: the caller would store "this track has no grid".
    path = tmp_path / "track.wav"
    path.write_bytes(b"RIFF....WAVE" + b"\x00" * 64)
    with pytest.raises(UnsupportedContainerError):
        BeatgridEncoder().read_beatgrid(Track.from_path(path))
    with pytest.raises(UnsupportedContainerError):
        V2Encoder().read_cues(Track.from_path(path))


def test_the_old_mp3_named_classes_still_resolve():
    # pymix imports these by their old names; renaming them without an alias
    # would break the server on a patch release of this library.
    from pyserato.encoders.beatgrid_mp3_encoder import BeatgridMp3Encoder
    from pyserato.encoders.v2_mp3_encoder import V2Mp3Encoder

    assert BeatgridMp3Encoder is BeatgridEncoder
    assert V2Mp3Encoder is V2Encoder


def test_the_mp3_path_still_writes_geob_frames(tmp_path):
    # The seam must not have quietly changed what an MP3 gets: still a GEOB
    # frame, still keyed by description, still leaving its siblings alone.
    path = tmp_path / "track.mp3"
    path.write_bytes(mp3_bytes())
    Mp3TagIO(path).write("Serato Overview", b"\x01\x05keep me")
    Mp3TagIO(path).write(MARKERS2, b"\x01\x01payload")

    tags = MP3(path)
    assert tags["GEOB:Serato Markers2"].data == b"\x01\x01payload"
    assert tags["GEOB:Serato Markers2"].mime == "application/octet-stream"
    assert tags["GEOB:Serato Overview"].data == b"\x01\x05keep me"
