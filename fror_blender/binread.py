import struct
import os
from enum import StrEnum


class Endianness(StrEnum):
    LITTLE = "<"
    BIG = ">"
    NATIVE = "@"


class BinaryReader:
    def __init__(self, f):
        self.f = f

    def seek(self, offset, whence=os.SEEK_SET):
        return self.f.seek(offset, whence)

    def tell(self):
        return self.f.tell()

    def skip(self, offset):
        return self.f.seek(offset, os.SEEK_CUR)

    def read(self, size=None):
        return self.f.read(size)

    def read_struct(self, format, endianness):
        s = struct.Struct(str(endianness) + format)
        bs = self.read(s.size)
        return s.unpack(bs)

    def read_fixed_size_string(self, size, encoding="ascii"):
        value: bytes = self.read_struct(str(size) + "s")[0]
        value = value.rstrip(b"\0")
        value = value.decode(encoding)
        return value

    def read_s32(self, endianness):
        return self.read_struct("i", endianness)[0]

    def read_u32(self, endianness):
        return self.read_struct("I", endianness)[0]

    def read_s16(self, endianness):
        return self.read_struct("h", endianness)[0]

    def read_u16(self, endianness):
        return self.read_struct("H", endianness)[0]

    def read_float(self, endianness):
        return self.read_struct("f", endianness)[0]

    def read_list(self, length, read_element, endianness):
        value = []
        for _ in range(length):
            value.append(read_element(self, endianness))
        return value

    def read_tuple(self, length, read_element, endianness):
        return tuple(self.read_list(length, read_element, endianness))
