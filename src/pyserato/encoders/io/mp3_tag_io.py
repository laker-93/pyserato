from pathlib import Path
from typing import Optional, Union

from mutagen import id3
from mutagen.mp3 import MP3

from pyserato.encoders.io.tag_io import TagIO


class Mp3TagIO(TagIO):
    """Serato tags in an MP3: ID3v2 GEOB frames, one per tag, keyed by description.

    By description and never by index. An analysed track carries six GEOB frames
    in no guaranteed order, so an indexed read returns whichever happened to be
    written first and fails its version check on most real files.
    """

    def __init__(self, path: Union[Path, str]):
        self._path = Path(path)

    def read(self, description: str) -> Optional[bytes]:
        frame = MP3(self._path).get(f"GEOB:{description}")
        return None if frame is None else bytes(frame.data)

    def write(self, description: str, payload: bytes) -> None:
        mutagen_file = MP3(self._path)
        # Keyed assignment, so only this frame is replaced. Assigning the whole
        # GEOB array would take Analysis, Autotags, Overview, Markers_ and
        # Markers2 with it (laker-93/pyserato#9) -- minutes of analysis and any
        # manual gridding the user cannot get back.
        mutagen_file[f"GEOB:{description}"] = id3.GEOB(
            encoding=0,
            mime="application/octet-stream",
            desc=description,
            data=payload,
        )
        mutagen_file.save()
