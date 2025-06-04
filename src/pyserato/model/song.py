from dataclasses import dataclass, field
from pathlib import Path
import logging

from pyserato.model.hot_cue import HotCue
from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.offset import Offset
from pyserato.model.tempo import Tempo
from pyserato.util import closest_offset

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Song:
    path: str
    location: Path
    track_id: str = ''
    average_bpm: float = 0.0
    date_added: str = ''
    play_count: str = ''
    tonality: str = ''
    total_time: float = 0.0

    beatgrid: list[Tempo] = field(default_factory=list)
    hot_cues: list[HotCue] = field(default_factory=list)
    cue_loops: list[HotCue] = field(default_factory=list)
    tag_data: dict = field(default_factory=dict)

    def add_beatgrid_marker(self, tempo: Tempo):
        self.beatgrid.append(tempo)

    def add_hot_cue(self, hot_cue: HotCue):
        at_index = hot_cue.index
        if hot_cue.type == HotCueType.LOOP:
            self.cue_loops.insert(at_index, hot_cue)
        else:
            self.hot_cues.insert(at_index, hot_cue)

    def add_tag_data(self, source_name: str, tags: list):
        self.tag_data[source_name] = tags

    def get_tag_data(self, source_name: str):
        return self.tag_data[source_name]

    def apply_beatgrid_offsets(self, offsets: list[Offset]):
        try:
            for hot_cue in self.hot_cues:
                hot_cue.offset = closest_offset(hot_cue.start, offsets)
                hot_cue.apply_offset()

            for loop in self.cue_loops:
                loop.offset = closest_offset(loop.start, offsets)
                loop.apply_offset()
        except ValueError as e:
            logger.error(
                f'Error: {e} | Track: {self.filename()}'
            )
