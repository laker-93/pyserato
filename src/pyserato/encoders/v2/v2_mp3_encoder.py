import base64
import struct

from mutagen.mp3 import MP3
from mutagen import id3

from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.model.track import Track
from pyserato.util import split_string


class V2Mp3Encoder(BaseEncoder):
    @property
    def tag_name(self) -> str:
        return 'GEOB:Serato Markers2'

    @property
    def tag_version(self) -> bytes:
        return b'\x01\x01'

    @property
    def markers_name(self) -> str:
        return 'Serato Markers2'

    def write(self, track: Track):
        tagged_file = self._write(track, self._encode(track))
        tagged_file.save()

    def _write(self, track: Track, payload: bytes) -> MP3:
        mutagen_file = MP3(track.path)
        mutagen_file[self.tag_name] = id3.GEOB(
            encoding=0,
            mime='application/octet-stream',
            desc=self.markers_name,
            data=payload,
        )

        return mutagen_file

    def _encode(self, track: Track) -> bytes:
        payload = b''
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
        return data.replace(b'=', b'A')


    @staticmethod
    def _pad_payload(payload: bytes):
        """
        Used when writing the data to the tags
        """
        length = len(payload)
        if length < 468:
            return payload.ljust(468, b'\x00')

        return payload.ljust(982, b'\x00') + b'\x00'

    def _enrich_payload(self, payload: bytes, entries_count: int | None = None):
        header = self.tag_version
        if entries_count is not None:
            header += struct.pack('>I', entries_count)

        return header + payload
