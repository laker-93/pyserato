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