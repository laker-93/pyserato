import os
from pathlib import Path
from typing import Iterator, Optional
from typing_extensions import Self

from pyserato import util
from pyserato.util import DuplicateTrackError

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
        resolved = full_path.resolve()
        if resolved in self._song_paths:
            raise DuplicateTrackError(f"path {resolved} is already in the crate {self.name}")
        self._song_paths.add(resolved)

    def __str__(self):
        return f"Crate<{self.name}>"

    def __repr__(self):
        return f"Crate<{self.name}>"


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
        for crate, paths in self._resolve_path(crate):
            yield crate, subcrate_folder / paths

    def build_crates_from_filepath(self, filepath: Path) -> Crate:
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
            otrk_idx = crate_content.find("otrk".encode())
            if otrk_idx < 0:
                break
            assert "otrk".encode() == crate_content[otrk_idx: otrk_idx + len("otrk")]
            ptrk_idx = crate_content.find("ptrk".encode())
            otrk_section = crate_content[otrk_idx + len("otrk"): ptrk_idx]
            len_data = util.hexbin_to_int(otrk_section) - 8
            ptrk_size = util.int_to_hexbin(len_data)
            data_section_start_idx = ptrk_idx + len("ptrk") + len(ptrk_size)
            data_section = crate_content[data_section_start_idx:]
            data_section_end_idx = data_section.find("otrk".encode())
            if data_section_end_idx == -1:
                data_section_end_idx = data_section_start_idx + len_data
            data_section = data_section[:data_section_end_idx]
            file_path = util.from_serato_string(data_section.decode())
            if not file_path.startswith("/"):
                file_path = "/" + file_path
            yield Path(file_path)
            crate_content = crate_content[data_section_start_idx + data_section_end_idx:]

    @staticmethod
    def _build_save_buffer(crate: Crate) -> bytes:
        header = ("vrsn   8 1 . 0 / S e r a t o   S c r a t c h L i v e   C r a t e").replace(" ", "\0")
        # header = "vrsn 81.0/Serato ScratchLive Crate"

        playlist_section = bytes()
        if crate.song_paths:
            for song_path in crate.song_paths:
                absolute_song_path = Path(song_path).resolve()
                data = util.to_serato_string(str(absolute_song_path))
                ptrk_size = util.int_to_hexbin(len(data))
                otrk_size = util.int_to_hexbin(len(data) + 8)
                playlist_section += "otrk".encode()
                playlist_section += otrk_size
                playlist_section += "ptrk".encode()
                playlist_section += ptrk_size
                playlist_section += data.encode()

        contents = header.encode() + playlist_section
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
