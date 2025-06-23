from mutagen.mp3 import MP3

from pyserato.encoders.v2_mp3_encoder import V2Mp3Encoder
from pyserato.builder import Builder
from pyserato.model.track import Track
from pyserato.model.crate import Crate
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType

TAG_NAME = 'GEOB:Serato Markers2'
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
    mp3_encoder = V2Mp3Encoder()
    track = Track.from_path(track_path)
    cues = mp3_encoder.read_cues(track)
    print(cues)


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
    read_tags()
    #clear_tags()
    #write_tags()
