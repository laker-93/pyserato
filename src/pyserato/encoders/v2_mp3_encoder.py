"""Deprecated: the cue encoder is no longer MP3-only.

Kept so existing imports keep working. `V2Mp3Encoder` is `V2Encoder`; the name
was a description of a limitation, and the limitation is gone.
"""

from pyserato.encoders.v2_encoder import V2Encoder

V2Mp3Encoder = V2Encoder

__all__ = ["V2Encoder", "V2Mp3Encoder"]
