import re

INVALID_CHARACTERS_REGEX = re.compile(r"[^A-Za-z0-9_ ]", re.IGNORECASE)


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
