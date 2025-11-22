import struct
import os
from enum import StrEnum
import typing
import abc


class Endianness(StrEnum):
    LITTLE = "<"
    BIG = ">"
    NATIVE = "@"


T = typing.TypeVar("T", covariant=True)
A = typing.TypeVar("A", contravariant=True)
I = typing.TypeVar("I", contravariant=True)


class BinRead(typing.Protocol[T, A]):
    @staticmethod
    @abc.abstractmethod
    def binread(binary_reader: "BinaryReader", args: A, endianness: Endianness) -> T: ...


class BinaryReader:
    def __init__(self, f: typing.Any):
        self.f = f

    def seek(self, offset: int, whence: int = os.SEEK_SET):
        return self.f.seek(offset, whence)

    def tell(self):
        return self.f.tell()

    def skip(self, offset: int):
        return self.f.seek(offset, os.SEEK_CUR)

    def read(self, size: typing.Optional[int] = None):
        return self.f.read(size)

    def read_struct(self, format: str, endianness: Endianness) -> tuple[typing.Any]:
        s = struct.Struct(str(endianness) + format)
        bs = self.read(s.size)
        return s.unpack(bs)

    def read_fixed_size_string(self, size: int, encoding: str = "ascii") -> str:
        value: bytes = self.read_struct(str(size) + "s", Endianness.LITTLE)[0]
        value = value.rstrip(b"\0")
        return value.decode(encoding)

    def read_s32(self, endianness: Endianness) -> int:
        return self.read_struct("i", endianness)[0]

    def read_u32(self, endianness: Endianness) -> int:
        return self.read_struct("I", endianness)[0]

    def read_s16(self, endianness: Endianness) -> int:
        return self.read_struct("h", endianness)[0]

    def read_u16(self, endianness: Endianness) -> int:
        return self.read_struct("H", endianness)[0]

    def read_u16_args(self, args: None, endianness: Endianness) -> int:
        return self.read_u16(endianness)

    def read_float(self, endianness: Endianness) -> float:
        return self.read_struct("f", endianness)[0]

    def read_float_args(self, args: None, endianness: Endianness) -> float:
        return self.read_float(endianness)

    def read_list(
        self,
        length: int,
        read_element: typing.Callable[["BinaryReader", A, Endianness], T],
        args: A,
        endianness: Endianness,
    ) -> list[T]:
        value = []
        for _ in range(length):
            value.append(read_element(self, args, endianness))
        return value

    def read_list_iter(
        self,
        iterable: typing.Iterable[I],
        read_element: typing.Callable[["BinaryReader", tuple[I, A], Endianness], T],
        args: A,
        endianness: Endianness,
    ) -> list[T]:
        value = []
        for i in iterable:
            value.append(read_element(self, (i, args), endianness))
        return value

    def read_tuple_2(
        self,
        read_element: typing.Callable[["BinaryReader", A, Endianness], T],
        args: A,
        endianness: Endianness,
    ) -> tuple[T, T]:
        return read_element(self, args, endianness), read_element(
            self, args, endianness
        )

    def read_tuple_3(
        self,
        read_element: typing.Callable[["BinaryReader", A, Endianness], T],
        args: A,
        endianness: Endianness,
    ) -> tuple[T, T, T]:
        return (
            read_element(self, args, endianness),
            read_element(self, args, endianness),
            read_element(self, args, endianness),
        )


class BinaryWriter:
    def __init__(self, f: typing.Any):
        self.f = f

    def seek(self, offset: int, whence: int = os.SEEK_SET):
        return self.f.seek(offset, whence)

    def tell(self):
        return self.f.tell()

    def write(self, data: bytes):
        return self.f.write(data)

    def write_struct(
        self, value: typing.Any, format: str, endianness: Endianness
    ) -> int:
        s = struct.Struct(str(endianness) + format)
        data = s.pack(value)
        return self.write(data)

    def write_u32(self, value: int, endianness: Endianness) -> int:
        return self.write_struct(value, "I", endianness)
