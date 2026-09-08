"""Deprecated: the beat grid encoder is no longer MP3-only.

Kept so existing imports keep working. `BeatgridMp3Encoder` is
`BeatgridEncoder`; the name was a description of a limitation, and the
limitation is gone.
"""

from pyserato.encoders.beatgrid_encoder import BeatgridEncoder

BeatgridMp3Encoder = BeatgridEncoder

__all__ = ["BeatgridEncoder", "BeatgridMp3Encoder"]
