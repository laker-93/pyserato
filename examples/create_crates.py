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
    #    -root
    #        -lvl1_1
    #             - lvl2_1
    #             - lvl2_2

    builder = Builder()
    crate = builder.build_crates_from_filepath(Path('/Users/lukepurnell/Music/_Serato_/Subcrates/root%%lvl1_1%%lvl2_1.crate'))
    print(crate)
    #lvl2_1 = Crate('lvl2_1')
    #print(f"crate: {lvl2_1}")
    #lvl2_1.add_song(Path("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav"))
    #lvl1_1 = Crate('lvl1_1', children=[lvl2_1])
    #lvl1_1.add_song(Path("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3"))
    #root_crate = Crate('root', children=[lvl1_1])
    #builder.save(root_crate)



    #crate = Crate('test')
    #crate.add_song(Path('/Users/lukepurnell/Music/Music/Justin Grounds - The Moon Pulled Us Here EP/Justin Grounds - The Moon Pulled Us Here EP - 05 Winds of the World.mp3'))
    #builder.save(crate)

    subcrates_folder = DEFAULT_SERATO_FOLDER / "SubCrates"
    for crate_path in subcrates_folder.glob("*crate"):
        crate = builder.build_crates_from_filepath(crate_path)
        print(crate)