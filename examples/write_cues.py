import base64
import struct
from io import BytesIO

from mutagen.mp3 import MP3

from pyserato.encoders.utils import decode
from pyserato.encoders.v2.v2_mp3_encoder import V2Mp3Encoder
from pyserato.builder import Builder
from pyserato.model.track import Track
from pyserato.model.crate import Crate
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType

TAG_NAME = 'GEOB:Serato Markers2'
FMT_VERSION = 'BB'
TAG_VERSION = b'\x01\x01'
MARKERS_NAME = 'Serato Markers2'
STRUCT_LENGTH = 0x16
def read_tags():
    tags = MP3("/Users/lukepurnell/Downloads/Skee Mask - C/Skee Mask - C - 01 MDP2.mp3")
    tag_data = tags[TAG_NAME]
    data = tag_data.data
    print(data)


def _get_entry_count(buffer: BytesIO):
    return struct.unpack('>I', buffer.read(4))[0]

def _remove_null_padding(payload: bytes):
    """
    Used when reading the data from the tags
    """
    return payload[:payload.index(b'\x00')]



def _get_entry_name(fp) -> str:
    entry_name = b''
    for x in iter(lambda: fp.read(1), b''):
        if x == b'\00':
            return entry_name.decode('utf-8')

        entry_name += x

    return ''

def _pad_encoded_data(data: bytes):
    """
    Used when reading the data from the tags
    """
    padding = b'A==' if len(data) % 4 == 1 else (b'=' * (-len(data) % 4))

    return data + padding
def _entry_data(data: bytes):
    fp = BytesIO(data)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x01, 0x01)
    payload = fp.read()
    data = b''.join(_remove_null_padding(payload).split(b'\n'))
    data = _pad_encoded_data(data)
    decoded = base64.b64decode(data)

    fp = BytesIO(decoded)
    assert struct.unpack(FMT_VERSION, fp.read(2)) == (0x01, 0x01)

    while True:
        entry_name = _get_entry_name(fp)  # NULL byte between name and length is already omitted
        if len(entry_name) == 0:
            break  # End of data

        struct_length = struct.unpack('>I', fp.read(4))[0]
        assert struct_length > 0  # normally this should not happen
        entry_data = fp.read(struct_length)

        match entry_name:
            case 'COLOR':
                yield self._create_color_entry(struct.unpack('>c3s', entry_data))
            case 'CUE':
                yield self.__create_cue_entry(self._extract_cue_data(entry_data), EntryType.CUE)
            case 'LOOP':
                yield self.__create_cue_entry(self._extract_loop_data(entry_data), EntryType.LOOP)
            case 'BPMLOCK':
                yield self._create_bpm_lock_entry(struct.unpack('>?', entry_data))

def main():
    mp3_encoder = V2Mp3Encoder()
    builder = Builder(encoder=mp3_encoder)
    crate = Crate('test080625')
    track = Track.from_path("/Users/lukepurnell/Downloads/Skee Mask - C/Skee Mask - C - 01 MDP2.mp3")
    crate.add_track(track)
    track.add_hot_cue(HotCue(name='cue1', type=HotCueType.CUE, start=50, index=1))
    track.add_hot_cue(HotCue(name='loop1', type=HotCueType.LOOP, start=50, end=52, index=1))
    builder.save(crate)

if __name__ == '__main__':
    read_tags()