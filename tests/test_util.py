from pyserato.util import int_to_hexbin, hexbin_to_int


def test_int_to_hexbin():
    hexbin = int_to_hexbin(133)
    assert hexbin == b"\x00\x00\x00\x85"


def test_hexbin_to_int():
    assert 133 == hexbin_to_int(b"\x00\x00\x00\x85")


def test_int_to_hexbin_hexbin_to_int():
    for i in range(1, 1025):
        assert i == hexbin_to_int(int_to_hexbin(i))
