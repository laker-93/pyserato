from pathlib import Path
from pyserato.builder import DEFAULT_SERATO_FOLDER, Crate, Builder
from pyserato.model.track import Track

def main():
    builder = Builder()
    subcrates_folder = DEFAULT_SERATO_FOLDER / "SubCrates"
    crates = builder.parse_crates_from_root_path(subcrates_folder)
    root = crates['root']
    print(f'root crate {root}')
    q = [root]
    while len(q):
        n = q.pop(0)
        print(f'crate {n} tracks {n.tracks}')
        for children in n.children.values():
            q.append(children)



if __name__ == '__main__':
    main()