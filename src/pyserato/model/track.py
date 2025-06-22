from dataclasses import dataclass, field
from pathlib import Path
import logging
from typing import Optional

from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.tempo import Tempo

logger = logging.getLogger(__name__)


@dataclass
class Track:
    path: Path
    track_id: str = ""
    average_bpm: float = 0.0
    date_added: str = ""
    play_count: str = ""
    tonality: str = ""
    total_time: float = 0.0

    beatgrid: list[Tempo] = field(default_factory=list)
    hot_cues: list[HotCue] = field(default_factory=list)
    cue_loops: list[HotCue] = field(default_factory=list)

    @staticmethod
    def from_path(path: Path | str, user_root: Optional[Path] = None) -> "Track":
        """
        Adds a unique track path to the crate. Raises DuplicateTrackError if track path is already present in the Crate.
        :param track_path:
        :param user_root: Support adding an arbitrary root to the tracks.
        This is useful when run in a docker container and the path needs to refer to one on the host.
        :return:
        """
        if isinstance(path, str):
            path = Path(path)
        full_path = user_root / path if user_root else path
        # note the path on the system may not yet exist. This is acceptable. As long as the path of the track is present
        # on the host system where the Serato crates are located at the point of opening Serato, the tracks will be
        # found.
        # assert full_path.exists(), f"path of track does not exist {full_path}"
        resolved = full_path.expanduser().resolve()
        return Track(resolved)

    def add_beatgrid_marker(self, tempo: Tempo):
        self.beatgrid.append(tempo)

    def add_hot_cue(self, hot_cue: HotCue):
        assert len(self.hot_cues) < 8, "cannot have more than 8 hot cues on a track"
        assert len(self.cue_loops) < 4, "cannot have more than 4 loops on a track"
        at_index = hot_cue.index
        if hot_cue.type == HotCueType.LOOP:
            self.cue_loops.insert(at_index, hot_cue)
        else:
            self.hot_cues.insert(at_index, hot_cue)

    # TODO
    # def apply_beatgrid_offsets(self, offsets: list[Offset]):
    #     try:
    #         for hot_cue in self.hot_cues:
    #             hot_cue.offset = closest_offset(hot_cue.start, offsets)
    #             hot_cue.apply_offset()

    #         for loop in self.cue_loops:
    #             loop.offset = closest_offset(loop.start, offsets)
    #             loop.apply_offset()
    #     except ValueError as e:
    #         logger.error(f"Error: {e} | Track: {self.filename()}")

    def __eq__(self, other):
        return self.path == other.path

    def __hash__(self):
        return hash(self.path)
