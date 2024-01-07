import os
from pathlib import Path
from typing import Iterator, Optional
from typing_extensions import Self

from pyserato import util

DEFAULT_SERATO_FOLDER = Path(os.path.expanduser("~/Music/_Serato_"))


class Crate:
    def __init__(self, name: str, children: Optional[list[Self]] = None):
        self._children = children if children else []
        self.filename = util.sanitize_filename(name)
        self._song_paths: list[Path] = []

    @property
    def children(self) -> list[Self]:
        return self._children

    @property
    def song_paths(self) -> list[Path]:
        return self._song_paths

    def add_song(self, song_path: str, user_root: str = ''):
        """
        :param song_path:
        :param user_root: Support adding an arbitrary root to the songs.
        This is useful when run in a docker container and the path needs to refer to one on the host.
        :return:
        """
        resolved = Path(user_root + song_path).resolve()
        self._song_paths.append(resolved)


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
            path += f'{crate.filename}%%'
            children = crate.children
            if children:
                for child in children:
                    crates.append((child, path))
            yield crate, path.rstrip('%%') + '.crate'

    def _build_crate_filepath(self, crate: Crate, serato_folder: Path) -> Iterator[tuple[Crate, Path]]:
        subcrate_folder = serato_folder / "SubCrates"
        for crate, paths in self._resolve_path(crate):
            yield crate, subcrate_folder / paths

    @staticmethod
    def _build_save_buffer(crate: Crate) -> bytes:
        header = (
            "vrsn   8 1 . 0 / S e r a t o   S c r a t c h L i v e   C r a t e"
        ).replace(" ", "\0")

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

    def save(self, root: Crate, save_path: Path = DEFAULT_SERATO_FOLDER):
        for crate, filepath in self._build_crate_filepath(root, save_path):
            buffer = self._build_save_buffer(crate)
            filepath.write_bytes(buffer)
