from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Tempo:
    """One anchor of a Serato beat grid.

    Every anchor says "a beat falls here". What differs is what it says about
    the tempo after it:

      * a non-terminal anchor carries `beats_till_next` -- the whole number of
        beats until the following anchor -- and the tempo of that segment is
        whatever the spacing implies;
      * the final anchor carries an explicit `bpm` and runs to the end of the
        track.

    So `terminal` is a real distinction, not a position in a list. It is kept
    explicit for the same reason HotCue keeps its type explicit rather than
    inferring a loop from having an end: a marker mistyped by position silently
    loses the field that made it different, which has already cost us once on
    the cue side (laker-93/tserato#11).

    `position` is in seconds, which is what the frame stores.
    """

    position: Optional[float] = None
    bpm: Optional[float] = None
    beats_till_next: Optional[int] = None

    @property
    def terminal(self) -> bool:
        """True where this anchor carries a tempo rather than a beat count."""
        return self.beats_till_next is None
