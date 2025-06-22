from pyserato.encoders.base_encoder import BaseEncoder
from pyserato.encoders.serato_tags import SERATO_MARKERS_V1


class V1Mp3Encoder(BaseEncoder):
    STRUCT_LENGTH = 0x16

    @property
    def tag_name(self) -> str:
        return SERATO_MARKERS_V1

    @property
    def tag_version(self) -> bytes:
        return b"\x02\x05"

    @property
    def markers_name(self) -> str:
        return "Serato Markers_"
