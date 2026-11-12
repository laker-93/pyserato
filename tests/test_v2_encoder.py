"""V2Encoder's read side, on Markers2 payloads that differ from what it writes.

Serato pads Markers2's base64 text with NULs up to a minimum size, but a
payload that is already past that size can come with no NUL at all. pyserato
used to `index()` the first NUL, so a payload with none raised
`ValueError: subsection not found` and the track's cues were lost
(laker-93/pyserato#19). In production that was 147 of 259 MP3s in one upload.
"""

from pathlib import Path

from pyserato.encoders.io import tag_io_for
from pyserato.encoders.v2_encoder import V2Encoder

FIXTURES = Path(__file__).parent / "fixtures"


def _markers2(path: Path) -> bytes:
    encoder = V2Encoder()
    data = tag_io_for(path).read(encoder.markers_name)
    assert data is not None
    return data


def test_reads_cues_from_a_payload_with_no_nul_padding():
    encoder = V2Encoder()
    padded = _markers2(FIXTURES / "analysed.mp3")
    unpadded = padded.rstrip(b"\x00")
    assert b"\x00" not in unpadded[2:]  # the version header aside, no NUL left

    expected = list(encoder._decode(padded))
    assert len(expected) == 4  # the fixture's three CUEs and one LOOP
    assert list(encoder._decode(unpadded)) == expected


def test_reads_cues_from_a_payload_with_one_trailing_nul():
    encoder = V2Encoder()
    padded = _markers2(FIXTURES / "analysed.mp3")
    one_nul = padded.rstrip(b"\x00") + b"\x00"
    assert list(encoder._decode(one_nul)) == list(encoder._decode(padded))
