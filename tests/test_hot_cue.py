import struct
from io import BytesIO

import pytest
from pyserato.model.hot_cue import HotCue
from pyserato.model.serato_color import SeratoColor
from pyserato.model.hot_cue_type import HotCueType


def test_to_v2_bytes_cue_starts_with_header():
    hc = HotCue(name="cue1", type=HotCueType.CUE, start=254, index=0, color=SeratoColor.RED)
    cue_bytes = hc.to_v2_bytes()
    assert cue_bytes.startswith(b"CUE\x00")


def test_to_v2_bytes_loop_starts_with_header():
    hc = HotCue(name="loop1", type=HotCueType.LOOP, start=254, end=2405, index=0)
    loop_bytes = hc.to_v2_bytes()
    assert loop_bytes.startswith(b"LOOP\x00")


def _get_entry_name(fp) -> str:
    entry_name = b""
    for x in iter(lambda: fp.read(1), b""):
        if x == b"\00":
            return entry_name.decode("utf-8")
        entry_name += x

    return ""


def test_from_bytes_roundtrip():
    original = HotCue(name="cue_test", type=HotCueType.CUE, start=12345, index=3, color=SeratoColor.RED)
    bytes_data = original.to_v2_bytes()
    fp = BytesIO(bytes_data)
    entry_name = _get_entry_name(fp)
    assert entry_name == "CUE"
    struct_length = struct.unpack(">I", fp.read(4))[0]
    assert struct_length > 0  # normally this should not happen
    entry_data = fp.read(struct_length)
    parsed = HotCue.from_bytes(entry_data, HotCueType.CUE)
    assert parsed.name == original.name
    assert parsed.index == original.index
    assert parsed.start == original.start
    assert parsed.color == original.color


def test_from_bytes_rejects_loop_type():
    with pytest.raises(AssertionError, match="loop is unsupported"):
        HotCue.from_bytes(b"dummy", HotCueType.LOOP)
