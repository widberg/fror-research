from .binread import BinaryReader, Endianness
from dataclasses import dataclass


@dataclass
class ThreeDObjsPcEntry:
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

    def binread(binary_reader: BinaryReader, endianness: Endianness):
        a = binary_reader.read_list(12, BinaryReader.read_float, endianness)
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


def calculate_sum(arr: list[ThreeDObjsPcEntry]):
    sum = 0
    for i in range(len(arr)):
        elm = arr[i]
        sum += elm.the_first + elm.the_second
    return sum


def calculate_size(flags: int, w: int):
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
class MeshDescriptor:
    flags: int
    w: int
    num_vertices: int
    num_ngons: int
    data: bytes

    def binread(binary_reader: BinaryReader, endianness: Endianness):
        flags = binary_reader.read_u32(endianness)
        w = binary_reader.read_s16(endianness)
        num_vertices = binary_reader.read_u16(endianness)
        num_ngons = binary_reader.read_u16(endianness)
        data = binary_reader.read(calculate_size(flags, w) - 4 - 2 - 2 - 2)
        return MeshDescriptor(flags, w, num_vertices, num_ngons, data)


@dataclass
class NGon:
    indices: list[int]

    def binread(binary_reader: BinaryReader, endianness: Endianness):
        num_indices = binary_reader.read_u16(endianness)
        indices = binary_reader.read_list(
            num_indices, BinaryReader.read_u16, endianness
        )
        return NGon(indices)


@dataclass
class NGonBuffer:
    ngons: list[NGon]

    def binread(
        binary_reader: BinaryReader,
        mesh_descriptors: list[MeshDescriptor],
        i: int,
        endianness: Endianness,
    ):
        ngons = binary_reader.read_list(
            mesh_descriptors[i].num_ngons, NGon.binread, endianness
        )
        return NGonBuffer(ngons)


@dataclass
class ThreeDObjsPc:
    entries: list[ThreeDObjsPcEntry]
    mesh_descriptors: list[MeshDescriptor]
    ngon_buffers: list[NGonBuffer]

    def binread(binary_reader: BinaryReader, endianness: Endianness):
        num_entries = binary_reader.read_u32(endianness)
        binary_reader.skip(0xC)
        entries = binary_reader.read_list(
            num_entries, ThreeDObjsPcEntry.binread, endianness
        )
        sum = calculate_sum(entries)
        mesh_descriptors = binary_reader.read_list(
            sum, MeshDescriptor.binread, endianness
        )
        ngon_buffers = []
        for i in range(sum):
            ngon_buffers.append(
                NGonBuffer.binread(binary_reader, mesh_descriptors, i, endianness)
            )
        return ThreeDObjsPc(entries, mesh_descriptors, ngon_buffers)


def read_u16_float(binary_reader: BinaryReader, endianness: Endianness):
    value = binary_reader.read_u16(endianness)
    return float(value) / 0xFFFF


@dataclass
class VertexBuffer:
    positions: list[(float, float, float)]
    uvs: list[(float, float)]
    uvs2: list[(float, float)]

    def binread(
        binary_reader: BinaryReader, num_vertices: int, w: int, endianness: Endianness
    ):
        positions = []
        for _ in range(num_vertices):
            positions.append(
                binary_reader.read_tuple(3, BinaryReader.read_float, endianness)
            )
        uvs = []
        for _ in range(num_vertices):
            uvs.append(binary_reader.read_tuple(2, read_u16_float, endianness))
        uvs2 = []
        if w >= 0:
            for _ in range(num_vertices):
                uvs2.append(binary_reader.read_tuple(2, read_u16_float, endianness))
        return VertexBuffer(positions, uvs, uvs2)


@dataclass
class Mesh:
    vertex_buffer: VertexBuffer
    ngon_buffer: NGonBuffer
