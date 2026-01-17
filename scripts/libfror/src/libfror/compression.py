import contextlib
from io import BytesIO
import zlib
from .binrw import BinaryReader, BinaryWriter, Endianness
import typing
from pathlib import Path


def decompress(binary_reader: BinaryReader) -> bytes:
    decompressed_size = binary_reader.read_u32(Endianness.LITTLE)
    compressed_data = binary_reader.read()
    decompressed_data = zlib.decompress(compressed_data)
    assert len(decompressed_data) == decompressed_size
    return decompressed_data


def get_decompressed_binary_reader(f: typing.BinaryIO) -> BinaryReader:
    binary_reader = BinaryReader(f)
    decompressed_data = decompress(binary_reader)
    return BinaryReader(BytesIO(decompressed_data))


def get_decompressed_binary_reader_from_path(p: Path) -> BinaryReader:
    with open(p, "rb") as f:
        binary_reader = BinaryReader(f)
        decompressed_data = decompress(binary_reader)
        return BinaryReader(BytesIO(decompressed_data))


def compress_and_write(data: bytes, f: typing.BinaryIO) -> None:
    compressed_data = zlib.compress(data, level=9)
    binary_writer = BinaryWriter(f)
    binary_writer.write_u32(len(data), Endianness.LITTLE)
    binary_writer.write(compressed_data)
