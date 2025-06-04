from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Tempo:
    position: Optional[float] = None
    bpm: Optional[float] = None

    def __repr__(self) -> str:
        return f'BPM: {str(self.bpm).ljust(5)} starting @ {self._format_position()}'

    def _format_position(self) -> str:
        if self.position is None:
            return "None"

        if self.position < 0:
            return str(self.position)

        seconds = self.position / 1000
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)

        return f"{minutes:02d}:{remaining_seconds:02d}:{milliseconds:03d}"

    def set_position(self, value: float):
        # Beat grid starting positions cannot be negative (although Serato may represent them as such)
        self.position = round(value * 1000, 3)

    def set_bpm(self, value: float):
        self.bpm = round(value, 2)

    def get_position(self) -> Optional[float]:
        return self.position

    def get_bpm(self) -> Optional[float]:
        return self.bpm

    def get_beat_length(self) -> Optional[float]:
        if self.bpm:
            return (60 / self.bpm) * 1000
        return None
