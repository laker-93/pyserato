from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Tempo:
    position: Optional[float] = None
    bpm: Optional[float] = None
