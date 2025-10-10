import struct
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from pyserato.model.serato_color import SeratoColor
from pyserato.model.hot_cue_type import HotCueType


def write_null_terminated_string(s: str) -> bytearray:
    """Encode string as UTF-8 with a null terminator."""
    return bytearray(s.encode("utf-8") + b"\x00")


def concat_bytearrays(arrays: list[bytearray]) -> bytearray:
    result = bytearray()
    for arr in arrays:
        result.extend(arr)
    return result


def encode_element(name: str, data: bytes) -> bytearray:
    """Encode element with name, 4-byte big-endian length, and data."""
    name_bytes = write_null_terminated_string(name)
    length_bytes = struct.pack(">I", len(data))  # big-endian uint32
    return concat_bytearrays([name_bytes, bytearray(length_bytes), bytearray(data)])


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
            color=self.color.name,
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

    # @staticmethod
    # def _value_error(offset_name: str, new_pos: int, old_pos: int) -> ValueError:
    #     return ValueError(f"{offset_name} cannot go below 0. New position: {new_pos}, old position: {old_pos}")

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
        name_bytes = write_null_terminated_string(self.name)
        buf = bytearray(0x14 + len(name_bytes))

        # flags / header fields
        buf[0x0] = 0x00
        buf[0x1] = self.index

        struct.pack_into(">I", buf, 0x02, self.start)  # big-endian uint32
        struct.pack_into(">I", buf, 0x06, self.end)  # big-endian uint32

        buf[0x0E] = 0
        buf[0x0F] = 0
        buf[0x10] = 255
        buf[0x11] = 255
        buf[0x13] = 1

        # append name string
        buf[0x14: 0x14 + len(name_bytes)] = name_bytes

        return bytes(encode_element("LOOP", buf))

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
        return bytes(encode_element("CUE", data))

    @staticmethod
    def from_bytes(data: bytes, hotcue_type: HotCueType) -> "HotCue":
        fp = BytesIO(data)
        fp.seek(1)  # first byte is NULL as it's a separator
        if hotcue_type is HotCueType.CUE:
            result = (
                struct.unpack(">B", fp.read(1))[0],  # INDEX
                struct.unpack(">I", fp.read(4))[0],  # POSITION START
                struct.unpack(">B", fp.read(1))[0],  # NULL separator (aka POSITION END)
                None,  # aka. some field containing (4294967295, 39)
                struct.unpack(">3s", fp.read(3))[0],  # COLOR
                struct.unpack(">B", fp.read(1))[0],  # NULL separator
                struct.unpack(">?", fp.read(1))[0],  # LOCKED
                fp.read().partition(b"\x00")[0].decode("utf-8"),  # NAME + ending NULL separator
            )
            index, start, end, _1, color, _2, locked, name = result
            color = SeratoColor(color.hex().upper())
            hot_cue = HotCue(
                name=name,
                type=HotCueType.CUE,
                color=color,
                start=start,
                index=index,
            )
            return hot_cue
        elif hotcue_type is HotCueType.LOOP:
            index = struct.unpack(">B", fp.read(1))[0]
            start = struct.unpack(">I", fp.read(4))[0]
            end = struct.unpack(">I", fp.read(4))[0]

            # skip bytes 0x0E–0x13 (fixed flags and color placeholders)
            fp.seek(0x0E, 0)  # move to offset 0x0E in stream
            _ = fp.read(2)  # bytes 0x0E, 0x0F (color?)
            _ = fp.read(2)  # bytes 0x10, 0x11 (color?)
            _ = fp.read(1)  # byte 0x12 (padding 0)
            is_locked = struct.unpack(">B", fp.read(1))[0]  # byte 0x13 (locked = 1)

            # read the null-terminated name string
            name = fp.read().partition(b"\x00")[0].decode("utf-8")

            return HotCue(name=name, type=HotCueType.LOOP, start=start, end=end, index=index, is_locked=is_locked)
        else:
            raise ValueError(f"unknown type {hotcue_type}")
