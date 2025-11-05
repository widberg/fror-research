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
    null_index = value.find(b"\0")
    if null_index != -1:
        value = value[:null_index]
    value = value.decode("ascii")
    return value


@dataclass
class NPCEntry:
    name: str
    compressed_size: int
    offset: int
    decompressed_size: int


def main():
    parser = argparse.ArgumentParser(prog="NPC")
    parser.add_argument("npc")
    parser.add_argument("directory")
    args = parser.parse_args()

    directory = pathlib.Path(args.directory)

    with open(args.npc, "rb") as npc:
        num_entries = read_u32(npc)
        print(num_entries)

        entries: typing.List[NPCEntry] = []

        for _ in range(num_entries):
            name = read_fixed_string(npc, 64)
            print(name)
            compressed_size = read_u32(npc)
            assert(compressed_size == 0)
            offset = read_u32(npc)
            decompressed_size = read_u32(npc)
            entries.append(NPCEntry(name, compressed_size, offset, decompressed_size))

        data_offset = 4 + num_entries * (64 + 4 * 3)
        assert npc.tell() == data_offset

        for entry in entries:
            print(entry)
            npc.seek(data_offset + entry.offset)
            decompressed_data = npc.read(entry.decompressed_size)
            # decompressed_data = zlib.decompress(compressed_data)
            # assert len(decompressed_data) == entry.decompressed_size

            file_name = entry.name + ".wav"
            file_path = directory / file_name
            file_path_directory = file_path.parent
            file_path_directory.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(decompressed_data)


if __name__ == "__main__":
    main()
