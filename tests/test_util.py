from pyserato.util import int_to_hexbin


def test_int_to_hexbin():
    hexbin = int_to_hexbin(133)
    assert hexbin == b'\x00\x00\x00\x85'
