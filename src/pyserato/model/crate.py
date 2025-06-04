from copy import deepcopy
from itertools import zip_longest
from pathlib import Path
from typing import Optional, Self

from pyserato.model.song import Song
from pyserato.util import sanitize_filename, DuplicateTrackError


class Crate:
    def __init__(self, name: str, children: Optional[list[Self]] = None):
        self._children = children if children else []
        self.name = sanitize_filename(name)
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
        return Song(resolved)

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
