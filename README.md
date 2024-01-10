# pyserato
Programatically create crates in Serato.

Example use using the DEFAULT_SERATO_FOLDER.
This can be overwritten to a non default location by passing the desired root in to the `builder.save()` API.

```python
from pathlib import Path
from pyserato.crate import DEFAULT_SERATO_FOLDER, Crate, Builder

def list_crates_sync(serato_folder: Path = DEFAULT_SERATO_FOLDER) -> list[Crate]:
    all_crates = []
    subcrates_folder = serato_folder / "SubCrates"
    crates = [
        Crate(name.stem) for name in subcrates_folder.glob("*.crate")
    ]
    all_crates.extend(crates)
    return all_crates

if __name__ == '__main__':
    crates = list_crates_sync()
    print(crates)
    
    child_crate3 = Crate('child3')
    child_crate3.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
    child_crate = Crate('child1', children=[child_crate3])
    child_crate.add_song("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav")
    child_crate2 = Crate('child2')
    child_crate2.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
    child_crate.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
    root_crate = Crate('root', children=[child_crate, child_crate2])
    builder = Builder()
    builder.save(root_crate)
```

The following shows two different methods for creating the following Crate structure:

```python
    #    -root
    #        -lvl1_1
    #             - lvl2_1
    #             - lvl2_2
```

Option 1 (Depth First):

```Python
from pyserato.crate import Crate, Builder

builder = Builder()
lvl2_1 = Crate('lvl2_1')
lvl2_1.add_song("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav")
lvl1_1 = Crate('lvl1_1', children=[lvl2_1])
lvl1_1.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)


lvl2_2 = Crate('lvl2_2')
lvl2_2.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
lvl1_1 = Crate('lvl1_1', children=[lvl2_2])
lvl1_1.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)
```

Option 2 (Breadth First):

```Python
from pyserato.crate import Crate, Builder

builder = Builder()
lvl2_1 = Crate('lvl2_1')
lvl2_1.add_song("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav")
lvl2_2 = Crate('lvl2_2')
lvl2_2.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Cloud Formation.mp3")
lvl1_1 = Crate('lvl1_1', children=[lvl2_1, lvl2_2])
lvl1_1.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3")
root_crate = Crate('root', children=[lvl1_1])
builder.save(root_crate)
```
