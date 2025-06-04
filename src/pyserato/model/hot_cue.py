from dataclasses import dataclass, field
from typing import Optional, List

from pyserato.model.hot_cue_type import HotCueType
from pyserato.model.offset import Offset
from pyserato.util import rgb_to_hex


@dataclass
class HotCue:
    name: str
    type: HotCueType
    start: int
    index: int
    end: Optional[int] = None
    offset: Optional[Offset] = None

    _color: List[int] = field(default_factory=lambda: [0, 0, 0], repr=False)

    def __repr__(self):
        return 'Start: {start}{end} | Index: {index} | Name: `{name}`'.format(
            name=self.name,
            index=str(f'{self.index}').rjust(2),
            start=str(f'{self.start}ms').ljust(10),
            end=str(f' | End: {self.end}ms').ljust(10) if self.end is not None else ''
        )

    @property
    def color(self) -> List[int]:
        return self._color

    @color.setter
    def color(self, value: List[int]):
        if not isinstance(value, list) or len(value) != 3 or not all(isinstance(i, int) for i in value):
            raise ValueError("Color must be a list of three integers [R, G, B]")
        self._color = value

    def hex_color(self) -> str:
        return rgb_to_hex(*self._color)

    def apply_offset(self):
        if self.offset is None:
            return
        self._update_positions(int(self.offset.get_value()))

    def _update_positions(self, offset_value: int):
        if self.start is not None:
            old_start = self.start
            self.start += offset_value
            if self.start < 0:
                self.start = old_start
                raise self._value_error('Start time', self.start, old_start)

        if self.end is not None:
            old_end = self.end
            self.end += offset_value
            if self.end < 0:
                self.end = old_end
                raise self._value_error('End time', self.end, old_end)

    @staticmethod
    def _value_error(offset_name: str, new_pos: int, old_pos: int) -> ValueError:
        return ValueError(f'{offset_name} cannot go below 0. New position: {new_pos}, old position: {old_pos}')
