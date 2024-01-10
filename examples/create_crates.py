from pathlib import Path
from pyserato.crate import DEFAULT_SERATO_FOLDER, Crate, Builder


def list_crates(serato_folder: Path = DEFAULT_SERATO_FOLDER) -> list[Crate]:
    all_crates = []
    subcrates_folder = serato_folder / "SubCrates"
    crates = [
        Crate(name.stem) for name in subcrates_folder.glob("*.crate")
    ]
    all_crates.extend(crates)
    return all_crates


if __name__ == '__main__':
    crates = list_crates()
    print(crates)

    #    -root
    #        -lvl1_1
    #             - lvl2_1
    #             - lvl2_2

    builder = Builder()
    lvl2_1 = Crate('lvl2_1')
    print(f"crate: {lvl2_1}")
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
    root_crate = Crate('root')
    root_crate.add_song("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 To Compose To Decompose.mp3")
    builder.save(root_crate)
