from copy import deepcopy
from itertools import zip_longest
from typing import Optional
from typing_extensions import Self

from pyserato.model.track import Track
from pyserato.util import sanitize_filename, DuplicateTrackError


class Crate:
    def __init__(self, name: str, children: Optional[list[Self]] = None):
        self._children = children if children else []
        self.name = sanitize_filename(name)
        self._tracks: set[Track] = set()

    @property
    def children(self) -> list[Self]:
        return self._children

    @property
    def tracks(self) -> set[Track]:
        return self._tracks

    def add_track(self, track: Track) -> None:
        """
        Adds a unique Track to the Crate
        """
        if track in self._tracks:
            raise DuplicateTrackError(f"track {track} is already in the crate {self.name}")
        self._tracks.add(track)

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
        all_tracks = self._tracks | other._tracks
        for track in all_tracks:
            new.add_track(track)
        return new

    def __deepcopy__(self, memodict={}) -> "Crate":
        children_copy = []
        for child in self.children:
            children_copy.append(deepcopy(child))
        copy = Crate(self.name, children=children_copy)
        memodict[id(self)] = copy
        for track in self._tracks:
            copy.add_track(track)
        return copy

    def __eq__(self, other):
        result = self.name == other.name and self._tracks == other._tracks
        if self._children:
            # sort so order is deterministic
            children = sorted(self._children, key=lambda c: len(c.tracks))
            other_children = sorted(other._children, key=lambda c: len(c.tracks))
            for child, other_child in zip_longest(children, other_children):
                if child and other_child:
                    result &= child == other_child
                else:
                    result = False
        return result
