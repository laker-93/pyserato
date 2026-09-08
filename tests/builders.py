"""Synthetic audio files, built in code so the suite runs on CI.

Neither of these is playable and neither has ever been near Serato. They exist
so the container-handling tests have real MP3 and FLAC *structure* to work on --
mutagen must find a sync word or a STREAMINFO block, or it will not open the
file at all. Everything about Serato's own bytes is asserted against payloads
lifted from real analysed files, not against these.
"""

import struct
from pathlib import Path
from typing import Iterable, Optional

# One MPEG-1 Layer III frame: 128kbps, 44100Hz, no padding, silent payload.
# Enough for mutagen to find a sync word and treat the file as an MP3.
MPEG_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413


def mp3_bytes(frames: int = 20) -> bytes:
    return MPEG_FRAME * frames


def flac_bytes(
    comments: Optional[Iterable[str]] = (), padding: int = 256
) -> bytes:
    """A FLAC with a STREAMINFO, an APPLICATION block, Vorbis comments and padding.

    The APPLICATION and PADDING blocks are here to be *left alone*: a writer that
    rebuilds the block list instead of editing it drops them, and this is what
    notices.

    `comments=None` leaves out the Vorbis comment block entirely, which is a real
    state -- a FLAC nothing has ever tagged -- and the one where mutagen reports
    `tags` as None rather than as empty.
    """
    data = b"fLaC"
    data += _block(0, _streaminfo(), last=False)
    data += _block(2, b"riff" + b"\x00" * 8, last=False)
    if comments is not None:
        data += _block(4, _vorbis(comments), last=False)
    data += _block(1, b"\x00" * padding, last=True)
    return data


def write_flac(
    path: Path, comments: Optional[Iterable[str]] = (), padding: int = 256
) -> Path:
    path.write_bytes(flac_bytes(comments, padding))
    return path


def id3_prefixed(payload: bytes) -> bytes:
    """`payload` behind an ID3v2.4 tag, as some taggers leave a FLAC."""
    body = b"TIT2" + (14).to_bytes(4, "big") + b"\x00\x00" + b"\x03" + b"a leading tag\x00"
    size = bytes([(len(body) >> 21) & 0x7F, (len(body) >> 14) & 0x7F,
                  (len(body) >> 7) & 0x7F, len(body) & 0x7F])
    return b"ID3\x04\x00\x00" + size + body + payload


def _streaminfo() -> bytes:
    bits = "".join([
        format(4096, "016b"),   # min blocksize
        format(4096, "016b"),   # max blocksize
        format(0, "024b"),      # min framesize -- unknown
        format(0, "024b"),      # max framesize -- unknown
        format(44100, "020b"),  # sample rate
        format(2 - 1, "03b"),   # channels
        format(16 - 1, "05b"),  # bits per sample
        format(44100, "036b"),  # total samples: one second
    ])
    return int(bits, 2).to_bytes(18, "big") + b"\x00" * 16  # trailing md5


def _block(block_type: int, body: bytes, last: bool) -> bytes:
    return bytes([block_type | (0x80 if last else 0)]) + len(body).to_bytes(3, "big") + body


def _vorbis(comments: Iterable[str]) -> bytes:
    vendor = b"pyserato tests"
    comments = list(comments)
    out = struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", len(comments))
    for comment in comments:
        encoded = comment.encode("utf-8")
        out += struct.pack("<I", len(encoded)) + encoded
    return out
