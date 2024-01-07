import re

INVALID_CHARACTERS_REGEX = re.compile(r'[^A-Za-z0-9_ ]', re.IGNORECASE)


def to_serato_string(string: str) -> str:
    return '\0' + '\0'.join(list(string))


def int_to_hexbin(number: int) -> bytes:
    hex_str = format(number, '08x')
    ret = b''.join([bytes([int(hex_str[i:i + 2], 16)]) for i in range(0, len(hex_str), 2)])
    return ret


def sanitize_filename(filename: str) -> str:
    return re.sub(INVALID_CHARACTERS_REGEX, '-', filename)
