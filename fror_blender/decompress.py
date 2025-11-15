import zlib
from .binread import BinaryReader

def decompress(binary_reader: BinaryReader):
    decompressed_size = binary_reader.read_u32()
    compressed_data = binary_reader.read()
    decompressed_data = zlib.decompress(compressed_data)
    assert len(decompressed_data) == decompressed_size
    return decompressed_data
