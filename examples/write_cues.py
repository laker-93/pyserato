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
track_path = "/Users/lukepurnell/Downloads/Skee Mask - C/Skee Mask - C - 02 Bassline Dub.mp3"
TAG_NAME_V1 = 'GEOB:Serato Overview'
TAG_NAME_V1_2 = 'GEOB:Serato Markers_'
TAG_NAME_V1_3 = 'GEOB:Serato Analysis'


def clear_tags():
    track = MP3(track_path)
    tag_names = [TAG_NAME, TAG_NAME_V1, TAG_NAME_V1_2, TAG_NAME_V1_3]
    #tag_names = [TAG_NAME]
    for tn in tag_names:
        try:
            data = track.pop(tn)
        except Exception:
            pass
        else:
            print(data)
    track.save()

def read_tags():
    tags = MP3(track_path)
    tag_data = tags[TAG_NAME]
    data = tag_data.data
    assert data
    cues = list(_entry_data(data))
    print(cues)


def write_tags2():
    track = MP3(track_path)
    tag_data = track[TAG_NAME]
    tag_data.data = b'\x01\x01AQFDVUUAAAAADQAAAAHqIwAfrSYAAQAA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    track.save()

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
                continue
            case 'CUE':
                yield HotCue.from_bytes(entry_data, type=HotCueType.CUE)
            case 'LOOP':
                continue
            case 'BPMLOCK':
                continue

def write_tags():
    mp3_encoder = V2Mp3Encoder()
    builder = Builder(encoder=mp3_encoder)
    crate = Crate('test080625')
    track = Track.from_path(track_path)
    crate.add_track(track)
    track.add_hot_cue(HotCue(name='', type=HotCueType.CUE, start=1234, index=0))
    track.add_hot_cue(HotCue(name='', type=HotCueType.CUE, start=2234, index=1))
    track.add_hot_cue(HotCue(name='', type=HotCueType.CUE, start=3234, index=2))
    track.add_hot_cue(HotCue(name='', type=HotCueType.CUE, start=3234, index=3))
    track.add_hot_cue(HotCue(name='', type=HotCueType.CUE, start=3234, index=4))
    builder.save(crate, overwrite=True)

if __name__ == '__main__':
    #write_tags2()
    #read_tags()
    clear_tags()
    write_tags()
