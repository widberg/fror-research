import zlib
import argparse
import struct
from dataclasses import dataclass
import pathlib
import typing


def read_u32(f):
    u32_struct = struct.Struct("<I")
    bs = f.read(u32_struct.size)
    (value,) = u32_struct.unpack(bs)
    return value


def read_fixed_string(f, size):
    fixed_string_struct = struct.Struct(str(size) + "s")
    bs = f.read(fixed_string_struct.size)
    (value,) = fixed_string_struct.unpack(bs)
    value = value.rstrip(b"\0")
    value = value.decode("ascii")
    return value


@dataclass
class DBFEntry:
    name: str
    offset: int
    compressed_size: int
    decompressed_size: int


def main():
    parser = argparse.ArgumentParser(prog="DBF")
    parser.add_argument("dbf")
    parser.add_argument("directory")
    args = parser.parse_args()

    directory = pathlib.Path(args.directory)

    with open(args.dbf, "rb") as dbf:
        num_entries = read_u32(dbf)
        print(num_entries)

        entries: typing.List[DBFEntry] = []

        for _ in range(num_entries):
            name = read_fixed_string(dbf, 256)
            print(name)
            offset = read_u32(dbf)
            compressed_size = read_u32(dbf)
            decompressed_size = read_u32(dbf)
            entries.append(DBFEntry(name, offset, compressed_size, decompressed_size))

        data_offset = 4 + num_entries * (256 + 4 * 3)
        assert dbf.tell() == data_offset

        for entry in entries:
            print(entry)
            dbf.seek(data_offset + entry.offset)
            compressed_data = dbf.read(entry.compressed_size)
            decompressed_data = zlib.decompress(compressed_data)
            assert len(decompressed_data) == entry.decompressed_size

            file_path = directory / entry.name
            file_path_directory = file_path.parent
            file_path_directory.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(decompressed_data)


if __name__ == "__main__":
    main()
