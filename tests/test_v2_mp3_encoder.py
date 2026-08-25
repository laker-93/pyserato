"""Tests for pyserato.encoders.v2_mp3_encoder.V2Mp3Encoder."""

from pathlib import Path

from pyserato.encoders.v2_mp3_encoder import V2Mp3Encoder
from pyserato.model.track import Track


def _write_minimal_mp3(path: Path) -> None:
    """Write a minimal, valid MPEG1 Layer III mono frame stream.

    mutagen.mp3.MP3 needs to find a real MPEG audio frame sync to open the
    file at all, so a handful of repeated 32kbps/44100Hz mono frames (no
    payload data, just the header) are enough to produce a file mutagen can
    parse without needing any external tools like ffmpeg at test time.
    """
    # Frame header: MPEG1, Layer III, no CRC, 32kbps, 44100Hz, mono, no padding.
    header = bytes([0xFF, 0xFB, 0x10, 0xC0])
    frame_size = 104  # 144 * 32000 / 44100, floored, no padding byte
    frame = header + b"\x00" * (frame_size - len(header))
    path.write_bytes(frame * 5)


def test_read_cues_returns_empty_list_when_no_serato_tags(tmp_path):
    """A track never analysed by Serato has no Serato Markers2 frame at all.

    Regression test: read_cues used to raise KeyError in this case instead of
    returning an empty cue list, forcing callers to catch KeyError to
    distinguish "no cues" from "not analysed".
    """
    mp3_path = tmp_path / "no_tags.mp3"
    _write_minimal_mp3(mp3_path)

    encoder = V2Mp3Encoder()
    track = Track(path=mp3_path)

    assert encoder.read_cues(track) == []


def test_read_cues_returns_empty_list_when_tags_present_but_no_cues(tmp_path):
    """A track with a Serato Markers2 frame but zero cues also returns []."""
    mp3_path = tmp_path / "empty_cues.mp3"
    _write_minimal_mp3(mp3_path)

    encoder = V2Mp3Encoder()
    track = Track(path=mp3_path)
    encoder.write(track)  # writes a Serato Markers2 frame with no cues

    assert encoder.read_cues(track) == []
