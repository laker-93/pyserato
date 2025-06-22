import struct
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from pyserato.model.serato_color import SeratoColor
from pyserato.model.hot_cue_type import HotCueType


@dataclass
class HotCue:
    name: str
    type: HotCueType
    start: Optional[int]
    index: int
    end: Optional[int] = None
    is_locked: Optional[bool] = False
    color: SeratoColor = SeratoColor.RED

    def __repr__(self):
        return "Start: {start}{end} | Index: {index} | Name: {name} | Color: {color}".format(
            name=self.name,
            index=str(f"{self.index}").rjust(2),
            start=str(f"{self.start}ms").ljust(10),
            end=str(f" | End: {self.end}ms").ljust(10) if self.end is not None else "",
            color=self.color.name
        )

    # def apply_offset(self):
    #     if self.offset is None:
    #         return
    #     self._update_positions(int(self.offset.get_value()))

    # def _update_positions(self, offset_value: int):
    #     if self.start is not None:
    #         old_start = self.start
    #         self.start += offset_value
    #         if self.start < 0:
    #             self.start = old_start
    #             raise self._value_error("Start time", self.start, old_start)

    #     if self.end is not None:
    #         old_end = self.end
    #         self.end += offset_value
    #         if self.end < 0:
    #             self.end = old_end
    #             raise self._value_error("End time", self.end, old_end)

    @staticmethod
    def _value_error(offset_name: str, new_pos: int, old_pos: int) -> ValueError:
        return ValueError(f"{offset_name} cannot go below 0. New position: {new_pos}, old position: {old_pos}")

    def to_v2_bytes(self) -> bytes:
        if self.type == HotCueType.CUE:
            return self._cue_to_v2_bytes()
        elif self.type == HotCueType.LOOP:
            return self._loop_to_v2_bytes()
        raise ValueError(f"unsupported hotcue type {self.type}")

    def _loop_to_v2_bytes(self) -> bytes:
        """
                                            >B      c       I                   I               5s                      3s              >B      ?  # noqa: E501
        NAME    NULL    STRUCT LEN          NULL    INDEX   POS START           POS END         SOMETHING               COLOR                   LOCKED  NAME        NULL  # noqa: E501
        LOOP    \x00    \x00\x00\x00\x1f    \x00    \x00    \x00\x00\x00\xfe    \x00\x00\t%     \xff\xff\xff\xff\x00'   \xaa\xe1        \x00    \x00    first loop  \x00  # noqa: E501
        :param entry_data:
        :return:
        """
        data = b"".join(
            (
                struct.pack(">B", 0),
                struct.pack(">B", self.index),
                struct.pack(">I", self.start),
                struct.pack(">I", self.end),
                b"\xff\xff\xff\xff\x00",  # don't know what this is exactly
                struct.pack(">3s", b"\xaa\xe1"),  # color
                struct.pack(">B", 0),
                struct.pack(">?", False),  # is_locked
                self.name.encode("utf-8"),
                struct.pack(">B", 0),
            )
        )

        return b"".join([b"LOOP", b"\x00", struct.pack(">I", len(data)), data])

    def _cue_to_v2_bytes(self) -> bytes:
        """
        NAME   NULL  STRUCT LEN          NULL    INDEX   POS START           POS END   COLOR  NULL  LOCKED  NAME        NULL  # noqa: E501
        CUE    \x00  \x00\x00\x00\x16    \x00    \x00    \x00\x00\x00\xfe    \x00      \xc0&& \x00  \x00    first bar   \x00  # noqa: E501
        """
        data = b"".join(
            (
                struct.pack(">B", 0),
                struct.pack(">B", self.index),
                struct.pack(">I", self.start),
                struct.pack(">B", 0),
                struct.pack(">3s", bytes.fromhex(self.color.value)),
                struct.pack(">B", 0),
                struct.pack(">?", b"\x00"),
                self.name.encode("utf-8"),
                struct.pack(">B", 0),
            )
        )
        payload = b"".join([b"CUE", b"\x00", struct.pack(">I", len(data)), data])
        return payload

    @staticmethod
    def from_bytes(data: bytes, hotcue_type: HotCueType) -> "HotCue":
        assert hotcue_type == HotCueType.CUE, "loop is unsupported. TODO implement"
        fp = BytesIO(data)
        fp.seek(1)  # first byte is NULL as it's a separator

        result = (
            struct.unpack(">B", fp.read(1))[0],  # INDEX
            struct.unpack(">I", fp.read(4))[0],  # POSITION START
            struct.unpack(">B", fp.read(1))[0],  # NULL separator (aka POSITION END)
            None,  # aka. some field containing (4294967295, 39)
            struct.unpack(">3s", fp.read(3))[0],  # COLOR
            struct.unpack(">B", fp.read(1))[0],  # NULL separator
            struct.unpack(">?", fp.read(1))[0],  # LOCKED
            fp.read().partition(b"\x00")[0],  # NAME + ending NULL separator
        )
        index, start, end, _1, color, _2, locked, name = result
        color = SeratoColor(color.hex().upper())
        hot_cue = HotCue(
            name=name.decode("utf-8"),
            type=HotCueType.CUE,
            color=color,
            start=start,
            index=index,
        )
        return hot_cue
