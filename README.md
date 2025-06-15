# pyserato
Programmatically create and read/write Serato crates.

Example use using the DEFAULT_SERATO_FOLDER (~/Music/_Serato_).
This can be overwritten to a non default location by passing the desired root in to the `builder.save()` API.

## Writing Crates
The following shows two different methods for creating and writing the following Crate structure:

```python
    #    -root
    #        -lvl1_1
    #             - lvl2_1
    #             - lvl2_2
```

Option 1 (Depth First):

```Python
from pyserato.model.crate import Crate
from pyserato.builder import Builder

builder = Builder()
lvl2_1 = Crate('lvl2_1')
lvl2_1.add_track("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav")
lvl1_1 = Crate('lvl1_1', children=[lvl2_1])
lvl1_1.add_track("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)

lvl2_2 = Crate('lvl2_2')
lvl2_2.add_track("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
lvl1_1 = Crate('lvl1_1', children=[lvl2_2])
lvl1_1.add_track("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)
```

Option 2 (Breadth First):

```Python
from pyserato.model.crate import Crate
from pyserato.builder import Builder

builder = Builder()
lvl2_1 = Crate('lvl2_1')
lvl2_1.add_track("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav")
lvl2_2 = Crate('lvl2_2')
lvl2_2.add_track("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
lvl1_1 = Crate('lvl1_1', children=[lvl2_1, lvl2_2])
lvl1_1.add_track("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)
```

Songs added to crates must be unique. If not a DuplicateTrackError will be raised.
For example:

```python
from pyserato.model.crate import Crate

crate = Crate('foo')
crate.add_track('foo/bar/track.mp3')
crate.add_track('foo/bar/track.mp3')  # raises DuplicateTrackError
```

## Reading Crates

Reading Crates from file in to the `Crate` datastructure provided by this library.
```python
from pyserato.builder import Builder
builder = Builder()
subcrates_folder = DEFAULT_SERATO_FOLDER / "SubCrates"
crates = builder.parse_crates_from_root_path(subcrates_folder)
```

## Writing Cues & Loops

```python
from pyserato.encoders.v2.v2_mp3_encoder import V2Mp3Encoder
from pyserato.builder import Builder
from pyserato.model.track import Track
from pyserato.model.crate import Crate
from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType

mp3_encoder = V2Mp3Encoder()
builder = Builder(encoder=mp3_encoder)
crate = Crate('foo')
track = Track.from_path('path/to/song.mp3')
crate.add_track(track)
track.add_hot_cue(HotCue(name='cue1', type=HotCueType.CUE, start=50, index=1))
track.add_hot_cue(HotCue(name='loop1', type=HotCueType.LOOP, start=50, end=52, index=1))
builder.save(crate)
```
## Serato Database Format

See https://github.com/Holzhaus/serato-tags/
Serato stores its crate information in a directory called _Serato_/Subcrates in the root of the drive where the music is located (this is true when the music is on a removable drive, unclear what happens when it's on the primary drive of the computer). Each file in this directory corresponds to one crate and will be named CrateName.crate.
The crate hierachy tree is encoded in the CrateName.

The format of these .crate files is a concatenated sequence of records. Each record starts with a 4-byte ASCII tag, followed by a 4-byte big-endian length (always at least one), followed by the bytes of the record. The way the bytes are interpreted depends on the tag and follows this table:

Tag pattern	Data format
o*	Nested sequence of records
t*	UTF-16 big-endian text
p*	UTF-16 big-endian text, value is a path (relative to the root of the drive)
u*	Unsigned 32-bit big-endian value
s*	Signed 32-big big-endian value
b*	Byte value
vrsn	UTF-16 big-endian text, value is crate format version
Here are the meanings of specific fields:

Tag name	Meaning
otrk	Track
ptrk	Path to track file (nested inside otrk)
Here's an example of the structure of the .crate file:

  [
    ('vrsn', '1.0/Serato ScratchLive Crate'),
    ('otrk', [
      ('ptrk', 'Music/Daft Punk - 2001 - Discovery/06 Night Vision.mp3')]),
    ('otrk', [
      ('ptrk', 'Music/Daft Punk - 2013 - Random Access Memories/05 Instant Crush.mp3')]),
  ]
Note that the name of the crate is *not* encoded in the crate itself; it's only present in the filename. Also, some not-very-useful fields are omitted in this example; for example there appear to be fields that give the order that the title/artist/key/BPM columns should appear in the browser.

The encoding of the path of the file seems to change. Sometimes it is utf-8, other times it is latin-1. It is still not clear to me why this switch is made. The presence of a 'orvc' tag after a track path seems to indicate that latin-1 encoding is used. Else the default is utf-8.

## TODO
1. Parse additional Serato info.