from enum import Enum


class SeratoColor(str, Enum):
    """
    https://github.com/Holzhaus/serato-tags/blob/main/docs/colors.md#serato-dj-pro
    For Serato DJ Pro, saved and displayed colors are different. This map is the saved colors.
    """
    RED = "CC0000"
    ORANGE = "CC4400"
    AMBER = "CC8800"
    YELLOW = "CCCC00"
    LIME_GREEN = "88CC00"
    GREEN_YELLOW = "44CC00"
    GREEN = "00CC00"
    MINT_GREEN = "00CC44"
    TEAL_GREEN = "00CC88"
    TEAL = "00CCCC"
    SKY_BLUE = "0088CC"
    BLUE = "0044CC"
    DARK_BLUE = "0000CC"
    PURPLE = "4400CC"
    VIOLET = "8800CC"
    MAGENTA = "CC00CC"
    PINK = "CC0088"
    RED_PINK = "CC0044"
