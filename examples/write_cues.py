from pyserato.encoders.v2.v2_mp3_encoder import V2Mp3Encoder
from pyserato.builder import Builder
from pyserato.model.track import Track
from pyserato.model.crate import Crate
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType

def main():
    mp3_encoder = V2Mp3Encoder()
    builder = Builder(encoder=mp3_encoder)
    crate = Crate('test070625')
    track = Track.from_path("/Users/lukepurnell/Downloads/Skee Mask - C/Skee Mask - C - 06 One For Vertigo.mp3")
    crate.add_track(track)
    track.add_hot_cue(HotCue(name='cue1', type=HotCueType.CUE, start=50, index=1))
    track.add_hot_cue(HotCue(name='loop1', type=HotCueType.LOOP, start=50, end=52, index=1))
    builder.save(crate)

if __name__ == '__main__':
    main()