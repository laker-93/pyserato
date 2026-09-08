from pathlib import Path
from typing import Literal, Optional, Union

# The audio containers Serato writes its tags into.
Container = Literal["MP3", "FLAC", "WAV", "AIFF", "M4A", "Ogg"]

_SNIFF_BYTES = 16


def probe_container(path: Union[Path, str]) -> Container:
    """What this file actually is, from its bytes rather than its extension.

    A DJ library is full of files whose extension lies -- an AIFF saved as .wav,
    a FLAC named .mp3 by a download tool. Dispatching on the extension sends
    those to the wrong reader, which does not fail so much as quietly answer "no
    cues": the wrong answer rather than an error, and the one this whole seam
    exists to stop. The magic bytes cost one 16-byte read and cannot lie in the
    same way.
    """
    path = Path(path)
    head = _read_head(path)

    if head[:4] == b"fLaC":
        return "FLAC"

    if head[:3] == b"ID3":
        # Usually an MP3 -- but some taggers put an ID3v2 tag in front of a FLAC,
        # and mutagen's MP3 reader would open that tag quite happily and report
        # no Serato frames, which is a wrong answer rather than an error.
        after = _id3_tag_length(head)
        if after is not None and _read_head(path, after)[:4] == b"fLaC":
            # Only the container is reported, not where the FLAC stream starts:
            # mutagen finds it behind the tag on its own, and puts the tag back
            # on save. The TypeScript twin has to return an offset because the
            # FLAC parser it uses does not.
            return "FLAC"
        return "MP3"

    if head[:4] == b"RIFF":
        return "WAV"
    if head[:4] == b"FORM":
        return "AIFF"
    if head[:4] == b"OggS":
        return "Ogg"
    if head[4:8] == b"ftyp":
        return "M4A"

    # Anything not positively identified goes to the MP3 reader, which is where
    # it went before this function existed. A bare MPEG stream starts with a
    # frame sync, but plenty of real files start with neither that nor an ID3
    # tag -- leading junk, an APE tag -- and refusing those would break reads
    # that work today. Nothing is lost by trying: Serato keeps its tags in an
    # ID3v2 tag, so a file without one has no cues to find whatever it is.
    return "MP3"


def _read_head(path: Path, offset: int = 0) -> bytes:
    with path.open("rb") as fp:
        fp.seek(offset)
        return fp.read(_SNIFF_BYTES)


def _id3_tag_length(head: bytes) -> Optional[int]:
    """Total bytes of the ID3v2 tag at the start of `head`, or None if malformed."""
    if len(head) < 10:
        return None
    flags = head[5]
    size = 0
    for byte in head[6:10]:
        # Syncsafe: seven bits per byte, so a size byte can never look like a
        # frame sync. A set top bit means this is not a size field we understand.
        if byte & 0x80:
            return None
        size = (size << 7) | byte
    footer = 10 if flags & 0x10 else 0
    return 10 + size + footer
