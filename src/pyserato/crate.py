import os
from copy import deepcopy
from itertools import zip_longest
from pathlib import Path
from typing import Iterator, Optional
from typing_extensions import Self

from pyserato import util
from pyserato.util import DuplicateTrackError, serato_encode, serato_decode

DEFAULT_SERATO_FOLDER = Path(os.path.expanduser("~/Music/_Serato_"))


class Crate:
    def __init__(self, name: str, children: Optional[list[Self]] = None):
        self._children = children if children else []
        self.name = util.sanitize_filename(name)
        self._song_paths: set[Path] = set()

    @property
    def children(self) -> list[Self]:
        return self._children

    @property
    def song_paths(self) -> set[Path]:
        return self._song_paths

    def add_song(self, song_path: Path, user_root: Optional[Path] = None):
        """
        Adds a unique song path to the crate. Raises DuplicateTrackError if song path is already present in the Crate.
        :param song_path:
        :param user_root: Support adding an arbitrary root to the songs.
        This is useful when run in a docker container and the path needs to refer to one on the host.
        :return:
        """
        full_path = user_root / song_path if user_root else song_path
        # note the path on the system may not yet exist. This is acceptable. As long as the path of the track is present
        # on the host system where the Serato crates are located at the point of opening Serato, the tracks will be
        # found.
        # assert full_path.exists(), f"path of song does not exist {full_path}"
        resolved = full_path.expanduser().resolve()
        if resolved in self._song_paths:
            raise DuplicateTrackError(f"path {resolved} is already in the crate {self.name}")
        self._song_paths.add(resolved)

    def __str__(self):
        return f"Crate<{self.name}>"

    def __repr__(self):
        return f"Crate<{self.name}>"

    def __add__(self, other) -> "Crate":
        assert self.name == other.name
        children = self._children + other._children
        children_copy = []
        for child in children:
            children_copy.append(deepcopy(child))
        new = Crate(self.name, children=children_copy)
        song_paths = self._song_paths | other._song_paths
        for song in song_paths:
            new.add_song(song)
        return new

    def __deepcopy__(self, memodict={}) -> "Crate":
        children_copy = []
        for child in self.children:
            children_copy.append(deepcopy(child))
        copy = Crate(self.name, children=children_copy)
        memodict[id(self)] = copy
        for song_path in self.song_paths:
            copy.add_song(song_path)
        return copy

    def __eq__(self, other):
        result = self.name == other.name and self._song_paths == other._song_paths
        if self._children:
            for child, other_child in zip_longest(self._children, other._children):
                if child and other_child:
                    result &= child == other_child
                else:
                    result = False
        return result


class Builder:
    @staticmethod
    def _resolve_path(root: Crate) -> Iterator[tuple[Crate, str]]:
        """
        DFS through the crate tree returning a generator of paths with the current crate as the root.
        :return:
        """
        path = ""
        crates = [(root, path)]
        while crates:
            crate, path = crates.pop()
            path += f"{crate.name}%%"
            children = crate.children
            if children:
                for child in children:
                    crates.append((child, path))
            yield crate, path.rstrip("%%") + ".crate"

    @staticmethod
    def _parse_crate_names(filepath: Path) -> Iterator[str]:
        for name in str(filepath.name).split("%%"):
            yield name.replace(".crate", "")

    def _build_crate_filepath(self, crate: Crate, serato_folder: Path) -> Iterator[tuple[Crate, Path]]:
        subcrate_folder = serato_folder / "SubCrates"
        subcrate_folder.mkdir(exist_ok=True)
        for crate, paths in self._resolve_path(crate):
            yield crate, subcrate_folder / paths

    def parse_crates_from_root_path(self, subcrate_path: Path) -> dict[str, Crate]:
        crate_name_to_crate: dict[str, Crate] = {}
        for f in subcrate_path.iterdir():
            if not f.name.endswith('crate'):
                continue
            crate = self._build_crates_from_filepath(f)
            if crate.name in crate_name_to_crate:
                crate += crate_name_to_crate[crate.name]
                crate_name_to_crate[crate.name] = crate
            else:
                crate_name_to_crate[crate.name] = crate
        return crate_name_to_crate

    def _build_crates_from_filepath(self, filepath: Path) -> Crate:
        """
        Builds the crate tree from an existing file path.
        :param filepath:
        :return:
        """
        crate_names = list(self._parse_crate_names(filepath))
        child_crate = None
        crate = None
        for crate_name in reversed(crate_names):
            if child_crate is None:
                crate = Crate(crate_name)
                for song in self._parse_crate_songs(filepath):
                    crate.add_song(song)
                child_crate = crate
            else:
                crate = Crate(crate_name, children=[child_crate])
                child_crate = crate
        assert crate, f"no crates parsed from {filepath}"
        return crate

    @staticmethod
    def _parse_crate_songs(filepath: Path) -> Iterator[Path]:
        crate_content = filepath.read_bytes()
        while crate_content:
            otrk_idx = crate_content.find("otrk".encode("utf-8"))
            if otrk_idx < 0:
                break
            assert "otrk".encode("utf-8") == crate_content[otrk_idx: otrk_idx + len("otrk")]
            ptrk_idx = crate_content.find("ptrk".encode("utf-8"))
            # Below would be the lgnth of the otrk data if needed for further parsing.
            # otrk_section = crate_content[otrk_idx + len("otrk"): ptrk_idx]
            # len_data = int.from_bytes(otrk_section, "big") - 8
            ptrk_section = crate_content[ptrk_idx:]
            track_name_length = int.from_bytes(ptrk_section[4:8], "big")
            track_name_encoded = ptrk_section[8: 8 + track_name_length]
            file_path = serato_decode(track_name_encoded)
            if not file_path.startswith("/"):
                file_path = "/" + file_path

            yield Path(file_path)
            crate_content = crate_content[ptrk_idx + 8 + track_name_length:]

    @staticmethod
    def _build_save_buffer(crate: Crate) -> bytes:
        header = "vrsn".encode("latin1")
        # byteorder is redundant here for a size of 1 but is a required arg in Python 3.10-
        header += (0).to_bytes(1, byteorder="big")
        header += (0).to_bytes(1, byteorder="big")
        header += serato_encode("81.0")
        header += serato_encode("/Serato ScratchLive Crate")

        # sorting = "osrt".encode('latin1')
        # default_sorting_type = "song"
        # default_sorting_rev = (1 << 8)
        # sorting += (len(default_sorting_type) * 2 + 17).to_bytes(4, 'big')
        # sorting += "tvcn".encode('latin1')
        # sorting += (len(default_sorting_type) * 2).to_bytes(4, 'big')
        # sorting += default_sorting_type.encode('utf-16')
        # sorting += "brev".encode('latin1')
        # sorting += (default_sorting_rev).to_bytes(5, 'big')
        DEFAULT_COLUMNS = ["song", "artist", "album", "length"]
        column_section = bytes()
        for column in DEFAULT_COLUMNS:
            column_section += "ovct".encode()
            column_section += (len(column) * 2 + 18).to_bytes(4, "big")
            column_section += "tvcn".encode()
            column_section += (len(column) * 2).to_bytes(4, "big")
            column_section += serato_encode(column)
            column_section += "tvcw".encode()
            column_section += (2).to_bytes(4, "big")
            column_section += "0".encode()
            column_section += "0".encode()

        playlist_section = bytes()
        if crate.song_paths:
            for song_path in crate.song_paths:
                absolute_song_path = Path(song_path).resolve()

                otrk_size = (len(str(absolute_song_path)) * 2 + 8).to_bytes(4, "big")
                ptrk_size = (len(str(absolute_song_path)) * 2).to_bytes(4, "big")
                playlist_section += "otrk".encode("latin1")
                playlist_section += otrk_size
                playlist_section += "ptrk".encode("latin1")
                playlist_section += ptrk_size
                playlist_section += serato_encode(str(absolute_song_path))

        contents = header + column_section + playlist_section
        return contents

    def save(
        self,
        root: Crate,
        save_path: Path = DEFAULT_SERATO_FOLDER,
        overwrite: bool = False,
    ):
        for crate, filepath in self._build_crate_filepath(root, save_path):
            if filepath.exists() and overwrite is False:
                continue
            buffer = self._build_save_buffer(crate)
            filepath.write_bytes(buffer)
