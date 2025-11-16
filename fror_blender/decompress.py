from io import BytesIO
import zlib
from .binread import BinaryReader, Endianness


def decompress(binary_reader: BinaryReader):
    decompressed_size = binary_reader.read_u32(Endianness.LITTLE)
    compressed_data = binary_reader.read()
    decompressed_data = zlib.decompress(compressed_data)
    assert len(decompressed_data) == decompressed_size
    return decompressed_data


def get_decompressed_binary_reader(f):
    binary_reader = BinaryReader(f)
    decompressed_data = decompress(binary_reader)
    return BinaryReader(BytesIO(decompressed_data))
