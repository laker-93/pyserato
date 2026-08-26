import struct
from io import BytesIO

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


def test_cue_from_bytes_roundtrip():
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


def test_loop_from_bytes_roundtrip():
    original = HotCue(name="loop_test", type=HotCueType.LOOP, start=12345, end=34567, index=3, color=SeratoColor.RED)
    bytes_data = original.to_v2_bytes()
    fp = BytesIO(bytes_data)
    entry_name = _get_entry_name(fp)
    assert entry_name == "LOOP"
    struct_length = struct.unpack(">I", fp.read(4))[0]
    assert struct_length > 0  # normally this should not happen
    entry_data = fp.read(struct_length)
    parsed = HotCue.from_bytes(entry_data, HotCueType.LOOP)
    assert parsed.name == original.name
    assert parsed.index == original.index
    assert parsed.start == original.start
    assert parsed.end == original.end
    assert parsed.color == original.color


# The locked byte. Captured from a real Serato DJ Pro-authored MP3: a CUE in
# slot 2 at 0ms, amber, unnamed. Serato writes 0x00 in the LOCKED field for its
# own cues, which is what makes this a usable oracle for what pyserato should
# emit -- see the CUE docstring, which has always documented it as \x00.
SERATO_AUTHORED_CUE = bytes.fromhex("00010000000000cc8800000000")
LOCKED_OFFSET = 11


def _payload(hot_cue: HotCue) -> bytes:
    """The entry body, minus the name/length envelope encode_element adds."""
    fp = BytesIO(hot_cue.to_v2_bytes())
    _get_entry_name(fp)
    length = struct.unpack(">I", fp.read(4))[0]
    return fp.read(length)


def test_cue_matches_serato_authored_bytes_exactly():
    hc = HotCue(name="", type=HotCueType.CUE, start=0, index=1, color=SeratoColor.AMBER)
    assert _payload(hc) == SERATO_AUTHORED_CUE


def test_cue_is_unlocked_by_default():
    hc = HotCue(name="cue1", type=HotCueType.CUE, start=254, index=0, color=SeratoColor.RED)
    assert _payload(hc)[LOCKED_OFFSET] == 0x00


def test_cue_locked_byte_follows_is_locked():
    unlocked = HotCue(name="c", type=HotCueType.CUE, start=1, index=0, is_locked=False)
    locked = HotCue(name="c", type=HotCueType.CUE, start=1, index=0, is_locked=True)
    assert _payload(unlocked)[LOCKED_OFFSET] == 0x00
    assert _payload(locked)[LOCKED_OFFSET] == 0x01


def test_loop_locked_byte_follows_is_locked():
    unlocked = HotCue(name="l", type=HotCueType.LOOP, start=1, end=2, index=0, is_locked=False)
    locked = HotCue(name="l", type=HotCueType.LOOP, start=1, end=2, index=0, is_locked=True)
    assert _payload(unlocked)[0x13] == 0x00
    assert _payload(locked)[0x13] == 0x01


def test_cue_is_locked_survives_a_roundtrip():
    for is_locked in (False, True):
        original = HotCue(name="c", type=HotCueType.CUE, start=99, index=2, is_locked=is_locked)
        parsed = HotCue.from_bytes(_payload(original), HotCueType.CUE)
        assert parsed.is_locked == is_locked


def test_loop_is_locked_survives_a_roundtrip():
    for is_locked in (False, True):
        original = HotCue(name="l", type=HotCueType.LOOP, start=99, end=200, index=1, is_locked=is_locked)
        parsed = HotCue.from_bytes(_payload(original), HotCueType.LOOP)
        assert bool(parsed.is_locked) == is_locked
