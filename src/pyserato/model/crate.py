from typing import Optional
from typing_extensions import Self

from pyserato.model.track import Track
from pyserato.util import sanitize_filename, DuplicateTrackError


class Crate:
    def __init__(self, name: str, children: Optional[dict[str, Self]] = None):
        self._children = children if children else {}
        self.name = sanitize_filename(name)
        self._tracks: set[Track] = set()

    @property
    def children(self) -> dict[str, Self]:
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

    def __eq__(self, other):
        "comparison for two root crates"
        if self.name != other.name:
            return False
        if self.children.keys() != other.children.keys():
            return False
        for child_name in self.children:
            if self.children[child_name] != other.children[child_name]:
                return False
        return True
