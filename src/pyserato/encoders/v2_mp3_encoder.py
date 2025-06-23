import base64
import struct
from io import BytesIO
from typing import List, Iterator

from mutagen.mp3 import MP3
from mutagen import id3

from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.encoders.serato_tags import SERATO_MARKERS_V2
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.track import Track
from pyserato.util import split_string


class V2Mp3Encoder(BaseEncoder):

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
        tagged_file = self._write(track, self._encode(track))
        tagged_file.save()

    def read_cues(self, track: Track) -> List[HotCue]:
        tags = MP3(track.path)
        tag_data = tags[self.tag_name]
        data = tag_data.data
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
                    # not yet implemented
                    continue
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

    def _write(self, track: Track, payload: bytes) -> MP3:
        mutagen_file = MP3(track.path)
        mutagen_file[self.tag_name] = id3.GEOB(
            encoding=0,
            mime="application/octet-stream",
            desc=self.markers_name,
            data=payload,
        )

        return mutagen_file

    def _encode(self, track: Track) -> bytes:
        payload = b""
        for cue in track.hot_cues:
            payload += cue.to_v2_bytes()
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
