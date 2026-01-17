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


class BinRead(typing.Protocol[A]):
    @classmethod
    @abc.abstractmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: A, endianness: Endianness
    ) -> typing.Self: ...


class BinaryReader:
    def __init__(self, f: typing.Any):
        self.f = f

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
        self.f.seek(offset, whence)

    def tell(self) -> int:
        return self.f.tell()

    def skip(self, offset: int) -> None:
        self.f.seek(offset, os.SEEK_CUR)

    def read(self, size: typing.Optional[int] = None) -> bytes:
        return self.f.read(size)

    def read_struct(self, format: str, endianness: Endianness) -> tuple[typing.Any]:
        s = struct.Struct(str(endianness) + format)
        bs = self.read(s.size)
        return s.unpack(bs)

    def read_null_terminated_string(self, encoding: str = "ascii") -> str:
        value: bytearray = bytearray()
        while True:
            c = self.read_u8(Endianness.NATIVE)
            if c == 0:
                break
            value.append(c)
        return value.decode(encoding)

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

    def read_u8(self, endianness: Endianness) -> int:
        return self.read_struct("B", endianness)[0]

    def read_u8_args(self, args: None, endianness: Endianness) -> int:
        return self.read_u8(endianness)

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
        read_element: typing.Callable[["BinaryReader", I, Endianness], T],
        endianness: Endianness,
    ) -> list[T]:
        value = []
        for i in iterable:
            value.append(read_element(self, i, endianness))
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


class BinWrite(typing.Protocol[A]):
    @classmethod
    @abc.abstractmethod
    def binwrite(
        cls,
        binary_writer: "BinaryWriter",
        value: typing.Self,
        args: A,
        endianness: Endianness,
    ) -> None: ...


class BinaryWriter:
    def __init__(self, f: typing.Any):
        self.f = f

    def seek(self, offset: int, whence: int = os.SEEK_SET):
        return self.f.seek(offset, whence)

    def tell(self):
        return self.f.tell()

    def write(self, data: bytes) -> int:
        return self.f.write(data)

    def write_string(self, value: str, encoding: str = "ascii") -> None:
        self.write(value.encode(encoding))

    def write_null_terminated_string(self, value: str, encoding: str = "ascii") -> None:
        self.write_string(value, encoding)
        self.write_u8(0, Endianness.NATIVE)

    def write_fixed_size_string(
        self, value: str, size: int, encoding: str = "ascii"
    ) -> None:
        data = value.encode(encoding)
        assert len(data) <= size
        self.write(data)
        self.write(b"\0" * (size - len(data)))

    def write_struct(
        self, value: typing.Any, format: str, endianness: Endianness
    ) -> None:
        s = struct.Struct(str(endianness) + format)
        data = s.pack(value)
        self.write(data)

    def write_u8(self, value: int, endianness: Endianness) -> None:
        self.write_struct(value, "B", endianness)

    def write_u8_args(self, value: int, args: None, endianness: Endianness) -> None:
        self.write_u8(value, endianness)

    def write_u32(self, value: int, endianness: Endianness) -> None:
        self.write_struct(value, "I", endianness)

    def write_u32_args(self, value: int, args: None, endianness: Endianness) -> None:
        self.write_u32(value, endianness)

    def write_s32(self, value: int, endianness: Endianness) -> None:
        self.write_struct(value, "i", endianness)

    def write_s32_args(self, value: int, args: None, endianness: Endianness) -> None:
        self.write_s32(value, endianness)

    def write_float(self, value: float, endianness: Endianness) -> None:
        self.write_struct(value, "f", endianness)

    def write_float_args(self, value: int, args: None, endianness: Endianness) -> None:
        self.write_float(value, endianness)

    def write_list(
        self,
        values: list[T],
        write_element: typing.Callable[["BinaryWriter", T, A, Endianness], None],
        args: A,
        endianness: Endianness,
    ) -> None:
        for value in values:
            write_element(self, value, args, endianness)


def align_to(alignment: int, value: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment
