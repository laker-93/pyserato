from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from pyserato.encoders.v2_mp3_encoder import V2Mp3Encoder
from pyserato.builder import Builder
from pyserato.model.track import Track
from pyserato.model.crate import Crate
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType

TAG_NAME = 'GEOB:Serato Markers2'
track_path = "/Users/lukepurnell/test music/Russian Circles - Gnosis/Russian Circles - Gnosis - 06 Betrayal.mp3"
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
    for cue in cues:
        print(cue)

def get_geob_tabs():
    tags = ID3(track_path)
    for frame in tags.getall("GEOB"):
        print(frame)

def write_tags():
    mp3_encoder = V2Mp3Encoder()
    builder = Builder(encoder=mp3_encoder)
    crate = Crate('foopython')
    track = Track.from_path(track_path)
    crate.add_track(track)
    track.add_hot_cue(HotCue(name='cue1', type=HotCueType.CUE, start=50, index=1))
    track.add_hot_cue(HotCue(name='looppython1', type=HotCueType.LOOP, start=1900, end=3600, index=1))
    track.add_hot_cue(HotCue(name='looppython2', type=HotCueType.LOOP, start=4900, end=8600, index=2))
    builder.save(crate, overwrite=True)
    # or
    #mp3_encoder.write(track)

if __name__ == '__main__':
    #write_tags2()
    #clear_tags()
    write_tags()
    #get_geob_tabs()
    read_tags()
