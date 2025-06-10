import re
from typing import Optional

from pyserato.model.offset import Offset

INVALID_CHARACTERS_REGEX = re.compile(r"[^A-Za-z0-9_ ]", re.IGNORECASE)


def split_string(string: bytes, after: int = 72, delimiter: bytes = b'\n'):
    pieces = []
    while len(string) > 0:
        pieces.append(string[:after])
        string = string[after:]

    return delimiter.join(pieces)

def closest(number: float, values: list[float]) -> Optional[float]:
    closest_value = None
    closest_distance = None

    for value in values:
        distance = abs(value - number)

        if closest_distance is None or distance < closest_distance:
            closest_distance = distance
            closest_value = value

    return closest_value


def closest_offset(number: float, offsets: list[Offset]) -> Optional[Offset]:
    closest_value = None
    closest_distance = None

    for offset in offsets:
        distance = offset.distance_to_source(number)

        if closest_distance is None or distance < closest_distance:
            closest_distance = distance
            closest_value = offset

    return closest_value

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return '{:02x}{:02x}{:02x}'.format(r, g, b)

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    hex_str = hex_str.lstrip('#')  # Remove '#' if present
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def serato_decode(s: bytes) -> str:
    """
    Decode a string that's been encoded in to bytes Serato style.
    This is a Python implementation of Java's bytes to string utf16 which Serato appears to use from looking at:
    https://github.com/markusschmitz53/serato-itch-sync
    :param s:
    :return:
    """
    result = ""
    while s:
        chunk = s[:2]
        chunk = chunk[::-1]
        result += chunk.decode("utf16")
        s = s[2:]
    return result


def serato_encode(s: str) -> bytes:
    """
    Encode a string Serato style.
    This is a Python implementation of Java's 'writeChars' which Serato appears to use from looking at:
    https://github.com/markusschmitz53/serato-itch-sync
    :param s:
    :return:
    """
    result = []
    for c in s:
        result.append(int.from_bytes(c.encode("utf16"), byteorder="big") >> 0 & 255)
        result.append(int.from_bytes(c.encode("utf16"), byteorder="big") >> 8 & 255)
    return bytes(result)


def hexbin_to_int(data: bytes) -> int:
    hex_str = "".join([format(byte, "02x") for byte in data])
    return int(hex_str, 16)


def sanitize_filename(filename: str) -> str:
    return re.sub(INVALID_CHARACTERS_REGEX, "-", filename)


class DuplicateTrackError(Exception):
    """
    Raised if a track is added to a crate for which the track's path resolves to an existing track path already in the
    crate.
    """
