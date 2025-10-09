from pathlib import Path
from pyserato.builder import DEFAULT_SERATO_FOLDER, Crate, Builder
from pyserato.model.track import Track


def list_crates(serato_folder: Path = DEFAULT_SERATO_FOLDER) -> list[Crate]:
    all_crates = []
    subcrates_folder = serato_folder / "SubCrates"
    crates = [
        Crate(name.stem) for name in subcrates_folder.glob("*.crate")
    ]
    all_crates.extend(crates)
    return all_crates

def make_crates():
    builder = Builder()
    lvl2_1 = Crate('lvl2_1')
    lvl2_1.add_track(Track.from_path("/Users/lukepurnell/test music/Russian Circles - Gnosis/Russian Circles - Gnosis - 06 Betrayal.mp3"))
    lvl2_2 = Crate('lvl2_2')
    lvl2_2.add_track(Track.from_path("/Users/lukepurnell/test music/Laker - Noise From The Ruliad/Laker - Noise From The Ruliad - 01 Escape.mp3"))
    lvl1_1 = Crate('lvl1_1', children=[lvl2_1, lvl2_2])
    lvl1_1.add_track(Track.from_path("/Users/lukepurnell/test music/Laker - Noise From The Ruliad/Laker - Noise From The Ruliad - 02 Points Break At Break Points.mp3"))
    root_crate = Crate('rootpyserato', children=[lvl1_1])
    builder.save(root_crate)


if __name__ == '__main__':
    make_crates()
    #    -root
    #        -lvl1_1
    #             - lvl2_1
    #             - lvl2_2

    #path = '/Users/lukepurnell/Music/_Serato_/Subcrates/all%%new serato crate%%nested%%new music.crate'
    #path = '/Users/lukepurnell/Music/_Serato_/Subcrates/all%%test.crate'
    #path = '/Users/lukepurnell/Music/_Serato_/Subcrates/all%%NOPLAYLIST.crate'
    #crate = builder.build_crates_from_filepath(Path(path))
    #print(crate)
    #lvl2_1 = Crate('lvl2_1')
    #print(f"crate: {lvl2_1}")
    #lvl2_1.add_song(Path("/Users/lukepurnell/nav_music/Russian Circles/Gnosis/01 Tupilak.wav"))
    #lvl1_1 = Crate('lvl1_1', children=[lvl2_1])
    #lvl1_1.add_song(Path("/Users/lukepurnell/nav_music/Laker/Noise From The Ruliad/00 Entropy Increasing.mp3"))
    #root_crate = Crate('root', children=[lvl1_1])
    #builder.save(root_crate)



    #child1_crate = Crate('test-child1')
    #child1_crate.add_song(Path("/Users/lukepurnell/Music/Russian Circles - Gnosis/Russian Circles - Gnosis - 03 Gnosis.mp3"))
    #child2_crate = Crate('test-child2', children=[child1_crate])
    #child2_crate.add_song(Path("/Users/lukepurnell/Music/Laker - Noise From The Ruliad/Laker - Noise From The Ruliad - 02 Points Break At Break Points.mp3"))
    #child3_crate = Crate('test-child3', children=[child1_crate])
    #child3_crate.add_song(Path("/Users/lukepurnell/Music/Laker - Noise From The Ruliad/Laker - Noise From The Ruliad - 07 To Compose To Decompose.mp3"))
    #root_crate = Crate('root', children=[child1_crate, child2_crate, child3_crate])
    #root_crate.add_song(Path("/Users/lukepurnell/Music/Justin Grounds - The Moon Pulled Us Here EP/Justin Grounds - The Moon Pulled Us Here EP - 02 Santa Margharita.mp3"))
    #crate.add_song(Path("/Users/lukepurnell/Music/serato_export_test/subbox_export/Cloudkicker/Solitude/05 - I’m Glad You Still Have a Sense of Humor….flac"))
    #crate.add_song(Path("/Users/lukepurnell/Music/beets/Arca/Arca/04 Urchin.mp3"))
    ##crate.add_song(Path("…"))
    #builder.save(root_crate)
