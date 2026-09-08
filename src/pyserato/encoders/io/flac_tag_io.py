import base64
from pathlib import Path
from typing import Optional, Union

from mutagen.flac import FLAC

from pyserato.encoders.io.tag_io import TagIO
from pyserato.util import split_string

# What FLAC files a Serato tag under. The name is the one part that changes
# between containers -- the payload behind it is byte-identical to the MP3's.
#
# Markers_ and Autotags are deliberately absent: no public description of the
# format records a FLAC field name for either, and guessing one would write a
# comment Serato never reads and no tool can clean up. Asking for one raises.
_VORBIS_FIELD = {
    "Serato Analysis": "serato_analysis",
    "Serato BeatGrid": "serato_beatgrid",
    "Serato Markers2": "serato_markers_v2",
    "Serato Overview": "serato_overview",
}

# The value is not the payload: it is a base64'd envelope carrying the same
# mime type and description an MP3's GEOB frame carries in its own header.
#
#     "application/octet-stream\0" "\0" "Serato Markers2\0" <payload>
#      ^ mime                      ^ filename (always empty)
#
# 42 bytes of prefix for Markers2. Serato writes the base64 unpadded and wrapped
# at 72 characters, the same width it wraps the Markers2 payload itself at.
_ENVELOPE_MIME = "application/octet-stream"
_WRAP_AT = 72


class FlacTagIO(TagIO):
    """Serato tags in a FLAC: base64'd Vorbis comments, one per tag.

    Verified against a real Serato-analysed FLAC (laker-93/pyserato#12) and
    against the most complete public description of the format
    (Holzhaus/serato-tags, docs/fileformats.md), which agrees.

    No offset handling here, unlike the TypeScript twin: mutagen finds the FLAC
    stream behind a leading ID3v2 tag on its own, and puts the tag back on save.
    `probe_container` still reports that case as FLAC so it reaches this class
    rather than the MP3 reader, which would have found an ID3 tag with no Serato
    frames in it and answered "no cues".
    """

    def __init__(self, path: Union[Path, str]):
        self._path = Path(path)

    def read(self, description: str) -> Optional[bytes]:
        field = _field_for(description)
        tags = FLAC(self._path).tags
        if tags is None:
            return None
        for key, value in tags:
            if key.lower() == field:
                return _unwrap(description, value)
        return None

    def write(self, description: str, payload: bytes) -> None:
        field = _field_for(description)
        flac = FLAC(self._path)
        if flac.tags is None:
            flac.add_tags()
        comments = flac.tags
        assert comments is not None  # add_tags() above, for mypy

        value = _wrap(description, payload)
        for i, (key, _) in enumerate(comments):
            if key.lower() == field:
                # In place, and keeping the key exactly as the file spells it.
                # Vorbis field names are case-insensitive per the spec, so
                # writing a different case leaves two comments Serato may read
                # in either order; `tags[field] = value` would do that, and
                # would move the comment to the end of the list as well.
                #
                # Assigned through a slice because mutagen's VCommentDict reads
                # a plain index as a *key*, not a position: `comments[i] = ...`
                # raises. A slice is the one form it passes to the underlying
                # list.
                comments[i:i + 1] = [(key, value)]
                break
        else:
            comments.append((field, value))
        # mutagen rewrites only the metadata blocks and shrinks the padding
        # block to fit, so the audio frames are not touched and the file does
        # not grow. Every other block -- seektable, application, pictures --
        # survives.
        flac.save()


def _field_for(description: str) -> str:
    try:
        return _VORBIS_FIELD[description]
    except KeyError:
        raise ValueError(
            f"no known FLAC field for the Serato tag {description!r}; "
            f"known tags are {', '.join(sorted(_VORBIS_FIELD))}"
        ) from None


def _wrap(description: str, payload: bytes) -> str:
    envelope = f"{_ENVELOPE_MIME}\0\0{description}\0".encode("latin1") + payload
    encoded = base64.b64encode(envelope).rstrip(b"=")
    return split_string(encoded, after=_WRAP_AT).decode("ascii")


def _unwrap(description: str, value: str) -> bytes:
    """The payload inside a Serato Vorbis comment.

    Tolerant on the way in and strict on the way out: the base64 is accepted
    padded or not and wrapped or not, because a file may have been through
    another tool, but a comment whose envelope names a different tag than the
    one asked for is refused rather than returned. A Markers2 payload handed to
    the beatgrid decoder does not fail -- it reads as a grid with an absurd
    number of markers.
    """
    encoded = "".join(value.split())
    envelope = base64.b64decode(encoded + "=" * (-len(encoded) % 4))

    fields = envelope.split(b"\0", 3)
    if len(fields) < 4:
        raise ValueError(f"{description} comment is not a Serato envelope")
    _mime, _filename, found, payload = fields
    if found.decode("latin1") != description:
        raise ValueError(
            f"expected a {description} envelope, found {found.decode('latin1')!r}"
        )
    return payload
