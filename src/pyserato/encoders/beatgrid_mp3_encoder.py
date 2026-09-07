import logging
import struct
from io import BytesIO
from typing import List

from mutagen import id3
from mutagen.mp3 import MP3

from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.encoders.serato_tags import SERATO_BEATGRID
from pyserato.model.tempo import Tempo
from pyserato.model.track import Track

logger = logging.getLogger(__name__)

# The byte after the markers. Nobody knows what it is for: the most complete
# public description of the format calls it "apparently random"
# (Holzhaus/serato-tags, docs/serato_beatgrid.md), and it is the one field here
# that is neither structure nor data we can interpret.
#
# Every file observed carries 0x00 -- 34 Serato-authored files on the QA
# machine, gridded and ungridded alike -- so this is what we write when there is
# nothing to copy. When there *is* something to copy we copy it, because the
# rule for a byte we cannot read is the same as the rule for the sibling GEOB
# frames: do not overwrite what you cannot reproduce.
_DEFAULT_FOOTER = b"\x00"


class BeatgridMp3Encoder(BaseEncoder):
    """Reads and writes `GEOB:Serato BeatGrid`.

    The layout, verified by decoding real analysed files rather than taken from
    a reverse-engineering write-up:

        version   uint8 uint8      = (1, 0)      # note: Markers2 is (1, 1)
        n_markers uint32be
        n-1 x     float32be position_s, uint32be beats_till_next
        1 x       float32be position_s, float32be bpm      # terminal marker
        footer    1 byte                         # meaning unknown; copied, not set

    This agrees field for field with the most complete public description of
    the format (Holzhaus/serato-tags, docs/serato_beatgrid.md), which was
    checked against it after the fact. Two things that write-up leaves open are
    settled here empirically: the version bytes it records only as "?" are
    (1, 0) on all 34 Serato-authored files on the QA machine, and the footer it
    calls "apparently random" is 0x00 on all 34. Neither is relied on -- an
    unfamiliar version reads as "no grid" rather than as a grid, and the footer
    is copied from the file rather than assumed.

    Worked examples:

        0100 00000001 3d3c3e82 432f0000 00   1 marker, pos=0.045958s, bpm=175.0
        0100 00000000 00                     analysed but not gridded

    That second state is common and is not an error: Serato writes the frame
    with zero markers for a track it has analysed but never gridded. It decodes
    to an empty grid, exactly as a missing frame does.

    Positions are float32 in the frame, so a value read back will not be bit-
    equal to the float64 that went in. Round trips are asserted to float32
    tolerance, not exactly.

    MP3 only, matching the cue encoder's limitation (laker-93/pyserato#12).
    """

    @property
    def fmt_version(self) -> str:
        return "BB"

    @property
    def tag_name(self) -> str:
        return SERATO_BEATGRID

    @property
    def tag_version(self) -> bytes:
        return b"\x01\x00"

    @property
    def markers_name(self) -> str:
        return "Serato BeatGrid"

    def read_beatgrid(self, track: Track) -> List[Tempo]:
        """The track's grid, or an empty list where it has none.

        Absent, present-but-ungridded and unreadable all give an empty grid: a
        caller that must tell "no grid" from "not gridded" should look for the
        frame itself. Nothing here raises on a real library's worth of files.
        """
        tags = MP3(track.path)
        # By description. A Serato-analysed track carries six GEOB frames in no
        # guaranteed order, so an index would read whichever happened to be
        # first and fail the version check on most real files.
        tag_data = tags.get(self.tag_name)
        if tag_data is None:
            return []
        try:
            return self._decode(tag_data.data)
        except (struct.error, AssertionError, ValueError) as exc:
            logger.warning("unreadable beatgrid on %s: %s", track.path, exc)
            return []

    def read_footer(self, track: Track) -> bytes:
        """The trailing byte of the track's existing beatgrid frame, if it has one.

        Kept separate from read_beatgrid because it is not part of the grid --
        it is a byte we carry rather than a byte we understand.
        """
        try:
            tag_data = MP3(track.path).get(self.tag_name)
        except Exception:
            return _DEFAULT_FOOTER
        if tag_data is None or len(tag_data.data) < 1:
            return _DEFAULT_FOOTER
        return bytes(tag_data.data)[-1:]

    def write(self, track: Track):
        # The file being written is very often one Serato has analysed and left
        # ungridded, which already has this frame and therefore already has a
        # footer byte. Writing a grid into it must not silently replace that
        # byte with a guess.
        payload = self._encode(track.beatgrid, footer=self.read_footer(track))
        tagged_file = self._write(track, payload)
        tagged_file.save()

    def _decode(self, data: bytes) -> List[Tempo]:
        fp = BytesIO(data)
        version = struct.unpack(self.fmt_version, fp.read(2))
        assert version == (0x01, 0x00), f"unexpected beatgrid version {version}"
        (n_markers,) = struct.unpack(">I", fp.read(4))

        grid: List[Tempo] = []
        for i in range(n_markers):
            chunk = fp.read(8)
            if len(chunk) < 8:
                raise ValueError(f"beatgrid claims {n_markers} markers, ran out at {i}")
            if i == n_markers - 1:
                position, bpm = struct.unpack(">ff", chunk)
                grid.append(Tempo(position=position, bpm=bpm))
            else:
                position, beats = struct.unpack(">fI", chunk)
                grid.append(Tempo(position=position, beats_till_next=beats))
        return grid

    def _encode(self, grid: List[Tempo], footer: bytes = _DEFAULT_FOOTER) -> bytes:
        payload = self.tag_version + struct.pack(">I", len(grid))
        for i, tempo in enumerate(grid):
            if tempo.position is None:
                raise ValueError(f"beatgrid marker {i} has no position")
            terminal = i == len(grid) - 1
            # Strict on write. The two marker shapes are one byte-width apart
            # and nothing downstream can tell them apart afterwards, so a grid
            # whose model disagrees with its position in the list is rejected
            # here rather than written as a plausible wrong answer.
            if terminal:
                if tempo.bpm is None:
                    raise ValueError("the last beatgrid marker must carry a bpm")
                payload += struct.pack(">ff", tempo.position, tempo.bpm)
            else:
                if tempo.beats_till_next is None:
                    raise ValueError(
                        f"beatgrid marker {i} is not the last and must carry "
                        f"beats_till_next"
                    )
                payload += struct.pack(">fI", tempo.position, tempo.beats_till_next)
        return payload + (footer or _DEFAULT_FOOTER)

    def _write(self, track: Track, payload: bytes) -> MP3:
        mutagen_file = MP3(track.path)
        # Keyed assignment, so only this frame is replaced. Assigning the whole
        # GEOB array would take Analysis, Autotags, Overview, Markers_ and
        # Markers2 with it (laker-93/pyserato#9, laker-93/tserato#9) -- minutes
        # of analysis and any manual gridding the user cannot get back.
        mutagen_file[self.tag_name] = id3.GEOB(
            encoding=0,
            mime="application/octet-stream",
            desc=self.markers_name,
            data=payload,
        )
        return mutagen_file

    @staticmethod
    def bpm_between(first: Tempo, second: Tempo) -> float:
        """The tempo Serato infers for the segment starting at `first`.

        Non-terminal markers store a beat count, not a tempo; the tempo is
        implied by the spacing. Exposed because it is the one piece of
        arithmetic in the format, and callers converting to a format that wants
        an explicit tempo per anchor (Rekordbox's TEMPO) need exactly this.
        """
        if first.beats_till_next is None:
            raise ValueError("the terminal marker's bpm is stored, not derived")
        if first.position is None or second.position is None:
            raise ValueError("both beatgrid markers must have a position")
        span = second.position - first.position
        if span <= 0:
            raise ValueError("beatgrid markers must be strictly increasing in time")
        return first.beats_till_next * 60.0 / span
