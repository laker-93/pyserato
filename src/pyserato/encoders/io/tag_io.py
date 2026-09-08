from abc import ABC, abstractmethod
from typing import Optional


class TagIO(ABC):
    """Where a Serato tag lives in one container, and nothing about what it means.

    Serato's payloads are container-independent -- the same bytes describe the
    same cues whether they came out of an MP3's GEOB frame or a FLAC's Vorbis
    comment -- so the encoders keep the format and this keeps the retrieval.
    Adding a container is then a new implementation here, not a branch inside
    every encoder.

    Tags are addressed by their Serato description ("Serato Markers2"), not by
    the name the container happens to file them under, because that name is
    exactly the part that varies.
    """

    @abstractmethod
    def read(self, description: str) -> Optional[bytes]:
        """The tag's raw payload, or None where the file does not carry it.

        None is a real answer and is not the same as empty. A track Serato has
        analysed but never gridded carries a beatgrid tag with zero markers,
        which is "no grid"; a track Serato has never seen carries no tag at all,
        which is "we cannot say". Collapsing the two is what makes an import
        report cues it never looked for (laker-93/pymix#145).
        """

    @abstractmethod
    def write(self, description: str, payload: bytes) -> None:
        """Replace that payload, leaving every other tag in the file alone.

        An analysed track carries six Serato tags, five of which no encoder here
        can reproduce -- Overview alone is minutes of analysis the user cannot
        get back. Writing one must never be writing the set
        (laker-93/pyserato#9).
        """


class UnsupportedContainerError(Exception):
    """Raised for a container pyserato has no reader for yet.

    Named rather than generic so a caller can tell "this format is not
    implemented" from "this file is broken" -- the first is routine in a real
    library and the second is worth a warning.
    """

    def __init__(self, container: str, path):
        self.container = container
        self.path = path
        super().__init__(
            f"{container} is not supported yet ({path}); "
            f"pyserato reads Serato tags from MP3 and FLAC"
        )
