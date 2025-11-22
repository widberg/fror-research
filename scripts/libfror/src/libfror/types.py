from .binread import BinaryReader, Endianness, BinRead
from dataclasses import dataclass
import typing
import zlib


@dataclass
class ThreeDObjsPcEntry(BinRead[None]):
    a: list[float]
    the_first: int
    m: int
    n: int
    o: int
    p: int
    the_second: int
    q: int
    r: int
    s: int
    t: int
    u: int
    v: int
    w: int
    x: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjsPcEntry":
        a = binary_reader.read_list(12, BinaryReader.read_float_args, None, endianness)
        the_first = binary_reader.read_u16(endianness)
        m = binary_reader.read_u16(endianness)
        n = binary_reader.read_u32(endianness)
        o = binary_reader.read_u32(endianness)
        p = binary_reader.read_u32(endianness)
        the_second = binary_reader.read_u16(endianness)
        q = binary_reader.read_u16(endianness)
        r = binary_reader.read_u32(endianness)
        s = binary_reader.read_u32(endianness)
        t = binary_reader.read_u32(endianness)
        u = binary_reader.read_u32(endianness)
        v = binary_reader.read_u32(endianness)
        w = binary_reader.read_u32(endianness)
        x = binary_reader.read_u32(endianness)
        return ThreeDObjsPcEntry(
            a, the_first, m, n, o, p, the_second, q, r, s, t, u, v, w, x
        )


def calculate_sum(arr: list[ThreeDObjsPcEntry]) -> int:
    sum = 0
    for i in range(len(arr)):
        elm = arr[i]
        sum += elm.the_first + elm.the_second
    return sum


def calculate_size(flags: int, w: int) -> int:
    size = 20
    cursor_0 = (flags >> 0) & 0xFF
    cursor_1 = (flags >> 8) & 0xFF
    cursor_2 = (flags >> 16) & 0xFF
    cursor_3 = (flags >> 24) & 0xFF
    if (cursor_1 & 8) != 0:
        size += 20
    if (cursor_1 & 1) != 0:
        size += 4
    if w == -1 or (cursor_0 & 2) != 0 or (cursor_0 & 4) != 0:
        size += 4
    if (cursor_0 & 8) != 0:
        size += 4
    if (cursor_0 & 0x10) != 0:
        size += 4
    if (cursor_0 & 0x40) != 0:
        size += 4
    if (cursor_0 & 0x80) != 0:
        size += 4
    if (cursor_1 & 0x10) != 0:
        size += 4
    if (cursor_1 & 0x80) != 0:
        size += 4
    if (cursor_2 & 1) != 0:
        size += 4
    return size


@dataclass
class MeshDescriptor(BinRead[None]):
    flags: int
    w: int
    num_vertices: int
    num_ngons: int
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "MeshDescriptor":
        flags = binary_reader.read_u32(endianness)
        w = binary_reader.read_s16(endianness)
        num_vertices = binary_reader.read_u16(endianness)
        num_ngons = binary_reader.read_u16(endianness)
        data = binary_reader.read(calculate_size(flags, w) - 4 - 2 - 2 - 2)
        return MeshDescriptor(flags, w, num_vertices, num_ngons, data)


@dataclass
class NGon(BinRead[None]):
    indices: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "NGon":
        num_indices = binary_reader.read_u16(endianness)
        indices = binary_reader.read_list(
            num_indices, BinaryReader.read_u16_args, None, endianness
        )
        return NGon(indices)


@dataclass
class NGonBuffer(BinRead[tuple[MeshDescriptor, None]]):
    ngons: list[NGon]

    @classmethod
    def binread(
        cls,
        binary_reader: BinaryReader,
        args: tuple[MeshDescriptor, None],
        endianness: Endianness,
    ) -> "NGonBuffer":
        mesh_descriptor, _ = args
        ngons = binary_reader.read_list(
            mesh_descriptor.num_ngons, NGon.binread, None, endianness
        )
        return NGonBuffer(ngons)


@dataclass
class ThreeDObjsPc(BinRead[None]):
    entries: list[ThreeDObjsPcEntry]
    mesh_descriptors: list[MeshDescriptor]
    ngon_buffers: list[NGonBuffer]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjsPc":
        num_entries = binary_reader.read_u32(endianness)
        binary_reader.skip(0xC)
        entries = binary_reader.read_list(
            num_entries, ThreeDObjsPcEntry.binread, None, endianness
        )
        sum = calculate_sum(entries)
        mesh_descriptors = binary_reader.read_list(
            sum, MeshDescriptor.binread, None, endianness
        )
        ngon_buffers = binary_reader.read_list_iter(
            mesh_descriptors, NGonBuffer.binread, None, endianness
        )
        return ThreeDObjsPc(entries, mesh_descriptors, ngon_buffers)


def read_u16_float(binary_reader: BinaryReader, args: None, endianness: Endianness):
    value = binary_reader.read_u16(endianness)
    return float(value) / 0xFFFF


@dataclass
class VertexBuffer(BinRead[tuple[int, int]]):
    positions: list[tuple[float, float, float]]
    uvs: list[tuple[float, float]]
    uvs2: list[tuple[float, float]]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: tuple[int, int], endianness: Endianness
    ) -> "VertexBuffer":
        num_vertices, w = args
        positions = binary_reader.read_list(
            num_vertices,
            lambda b, a, e: BinaryReader.read_tuple_3(
                b, BinaryReader.read_float_args, a, e
            ),
            None,
            endianness,
        )
        uvs = binary_reader.read_list(
            num_vertices,
            lambda b, a, e: BinaryReader.read_tuple_2(b, read_u16_float, a, e),
            None,
            endianness,
        )
        uvs2 = []
        if w >= 0:
            uvs2 = binary_reader.read_list(
                num_vertices,
                lambda b, a, e: BinaryReader.read_tuple_2(b, read_u16_float, a, e),
                None,
                endianness,
            )
        return VertexBuffer(positions, uvs, uvs2)


@dataclass
class Mesh:
    vertex_buffer: VertexBuffer
    ngon_buffer: NGonBuffer


@dataclass
class DBF(BinRead[None]):
    files: dict[str, bytes]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "DBF":
        num_entries = binary_reader.read_u32(endianness)

        @dataclass
        class DBFEntry(BinRead[None]):
            name: str
            offset: int
            compressed_size: int
            decompressed_size: int

            @classmethod
            def binread(
                cls, binary_reader: BinaryReader, args: None, endianness: Endianness
            ) -> DBFEntry:
                name = binary_reader.read_fixed_size_string(256)
                offset = binary_reader.read_u32(endianness)
                compressed_size = binary_reader.read_u32(endianness)
                decompressed_size = binary_reader.read_u32(endianness)
                return DBFEntry(name, offset, compressed_size, decompressed_size)

        entries = binary_reader.read_list(
            num_entries, DBFEntry.binread, None, endianness
        )

        data_offset = 4 + num_entries * (256 + 4 * 3)
        assert binary_reader.tell() == data_offset

        files: dict[str, bytes] = {}

        for entry in entries:
            binary_reader.seek(data_offset + entry.offset)
            compressed_data = binary_reader.read(entry.compressed_size)
            decompressed_data = zlib.decompress(compressed_data)
            assert len(decompressed_data) == entry.decompressed_size

            assert entry.name not in files
            files[entry.name] = decompressed_data

        return DBF(files)


@dataclass
class NPC(BinRead[None]):
    files: dict[str, bytes]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "NPC":
        num_entries = binary_reader.read_u32(endianness)

        @dataclass
        class NPCEntry(BinRead[None]):
            name: str
            compressed_size: int
            offset: int
            decompressed_size: int

            @classmethod
            def binread(
                cls, binary_reader: BinaryReader, args: None, endianness: Endianness
            ) -> NPCEntry:
                name = binary_reader.read_fixed_size_string(64)
                compressed_size = binary_reader.read_u32(endianness)
                assert compressed_size == 0
                offset = binary_reader.read_u32(endianness)
                decompressed_size = binary_reader.read_u32(endianness)
                return NPCEntry(name, compressed_size, offset, decompressed_size)

        entries = binary_reader.read_list(
            num_entries, NPCEntry.binread, None, endianness
        )

        data_offset = 4 + num_entries * (64 + 4 * 3)
        assert binary_reader.tell() == data_offset

        files: dict[str, bytes] = {}

        for entry in entries:
            binary_reader.seek(data_offset + entry.offset)
            decompressed_data = binary_reader.read(entry.decompressed_size)

            assert entry.name not in files
            files[entry.name] = decompressed_data

        return NPC(files)
