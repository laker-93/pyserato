from pyserato.util import serato_encode, serato_decode


def test_serato_encode_decode():
    test_s = "/Users/lukepurnell/Music/beets/Arca/Arca/10 Desafío.mp3"
    assert serato_decode(serato_encode(test_s)) == test_s
