from dataclasses import dataclass


@dataclass(frozen=True)
class Offset:
    _source_beat: float  # value in ms
    _dest_beat: float    # value in ms

    def __repr__(self):
        return 'Offset: `{value}` | Source beat: {src_bt} | Destination beat: {dst_bt}'.format(
            value=str(f'{int(self.get_value())}ms').ljust(7),
            src_bt=str(f'{int(self._source_beat)}ms').ljust(7),
            dst_bt=str(f'{int(self._dest_beat)}ms').ljust(7)
        )

    def distance_to_source(self, number: float) -> float:
        return abs(self._source_beat - number)

    def get_value(self) -> int:
        """
        :return: int Value of the offset in milliseconds
        """
        if self._dest_beat < 0:
            diff = self._source_beat - abs(self._dest_beat)
        else:
            diff = abs(self._dest_beat - self._source_beat)

        return int(diff if self._source_beat < self._dest_beat else -diff)
