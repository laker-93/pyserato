import base64
import struct
from io import BytesIO
from typing import List, Iterator

from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.encoders.io import tag_io_for
from pyserato.encoders.serato_tags import SERATO_MARKERS_V2
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.track import Track
from pyserato.util import split_string


class V2Encoder(BaseEncoder):
    """Reads and writes `Serato Markers2` -- the cues and loops on a track.

    MP3 and FLAC. The payload is the same in both; only where it is stored
    differs, which is what `pyserato.encoders.io` handles. Handed a container
    with no reader yet -- WAV, AIFF, M4A -- this raises
    UnsupportedContainerError rather than guessing (laker-93/pyserato#16).
    """

    @property
    def fmt_version(self) -> str:
        return "BB"

    @property
    def tag_name(self) -> str:
        return SERATO_MARKERS_V2

    @property
    def tag_version(self) -> bytes:
        return b"\x01\x01"

    @property
    def markers_name(self) -> str:
        return "Serato Markers2"

    def write(self, track: Track):
        tag_io_for(track.path).write(self.markers_name, self._encode(track))

    def read_cues(self, track: Track) -> List[HotCue]:
        """The track's cues and loops, or an empty list where it has none.

        A track Serato has never analysed has no Markers2 tag at all, which is
        no cues and not an error -- this used to raise KeyError, which every
        caller had to know to catch (laker-93/pyserato#8).
        """
        data = tag_io_for(track.path).read(self.markers_name)
        if data is None:
            return []
        return list(self._decode(data))

    def _decode(self, data: bytes) -> Iterator[HotCue]:
        fp = BytesIO(data)
        assert struct.unpack(self.fmt_version, fp.read(2)) == (0x01, 0x01)
        payload = fp.read()
        data = b"".join(self._remove_null_padding(payload).split(b"\n"))
        data = self._pad_encoded_data(data)
        decoded = base64.b64decode(data)

        fp = BytesIO(decoded)
        assert struct.unpack(self.fmt_version, fp.read(2)) == (0x01, 0x01)

        while True:
            entry_name = self._get_entry_name(fp)  # NULL byte between name and length is already omitted
            if len(entry_name) == 0:
                break  # End of data

            struct_length = struct.unpack(">I", fp.read(4))[0]
            assert struct_length > 0  # normally this should not happen
            entry_data = fp.read(struct_length)

            match entry_name:
                case "COLOR":
                    # not yet implemented
                    continue
                case "CUE":
                    yield HotCue.from_bytes(entry_data, hotcue_type=HotCueType.CUE)
                case "LOOP":
                    yield HotCue.from_bytes(entry_data, hotcue_type=HotCueType.LOOP)
                case "BPMLOCK":
                    # not yet implemented
                    continue

    def _get_entry_count(self, buffer: BytesIO):
        return struct.unpack(">I", buffer.read(4))[0]

    def _remove_null_padding(self, payload: bytes):
        """
        Used when reading the data from the tags
        """
        return payload[: payload.index(b"\x00")]

    def _get_entry_name(self, fp) -> str:
        entry_name = b""
        for x in iter(lambda: fp.read(1), b""):
            if x == b"\00":
                return entry_name.decode("utf-8")

            entry_name += x

        return ""

    def _pad_encoded_data(self, data: bytes) -> bytes:
        """
        Used when reading the data from the tags
        """
        padding = b"A==" if len(data) % 4 == 1 else (b"=" * (-len(data) % 4))

        return data + padding

    def _encode(self, track: Track) -> bytes:
        payload = b""
        for cue in track.hot_cues:
            payload += cue.to_v2_bytes()
        for loop in track.cue_loops:
            payload += loop.to_v2_bytes()
        return self._pad(payload)

    def _pad(self, payload: bytes, entries_count: int | None = None):
        """
        Serato adds null padding at the end of the string.
        When the payload length is under 512 it pads until that number
        WHEN the payload is over 512 it pads until 1025

        Also, the payload is split at 72 characters before padding is applied
        """
        # Append the version for the non-encoded payload
        payload = self.tag_version + payload
        payload = self._remove_encoded_data_pad(base64.b64encode(payload))
        payload = self._pad_payload(split_string(payload))
        payload = self._enrich_payload(payload, entries_count)

        return payload

    @staticmethod
    def _remove_encoded_data_pad(data: bytes):
        """
        Used when after the base64 encode when writing data to the tags
        """
        return data.replace(b"=", b"A")

    @staticmethod
    def _pad_payload(payload: bytes):
        """
        Used when writing the data to the tags
        """
        length = len(payload)
        if length < 468:
            return payload.ljust(468, b"\x00")

        return payload.ljust(982, b"\x00") + b"\x00"

    def _enrich_payload(self, payload: bytes, entries_count: int | None = None):
        header = self.tag_version
        if entries_count is not None:
            header += struct.pack(">I", entries_count)

        return header + payload
