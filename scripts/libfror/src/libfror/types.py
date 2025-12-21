from enum import IntEnum, StrEnum
import os
from .binrw import BinWrite, BinaryReader, BinaryWriter, Endianness, BinRead, align_to
from dataclasses import dataclass
import zlib


@dataclass
class ThreeDObjsPcEntry(BinRead):
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
class MeshDescriptor(BinRead):
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
class NGon(BinRead):
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
class NGonBuffer(BinRead):
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
class ThreeDObjsPc(BinRead):
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
class VertexBuffer(BinRead):
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
class DBFEntry(BinRead):
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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DBFEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_fixed_size_string(value.name, 256)
        binary_writer.write_u32(value.offset, endianness)
        binary_writer.write_u32(value.compressed_size, endianness)
        binary_writer.write_u32(value.decompressed_size, endianness)


@dataclass
class DBF(BinRead, BinWrite):
    files: dict[str, bytes]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "DBF":
        num_entries = binary_reader.read_u32(endianness)

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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DBF",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.files), endianness)

        entries_pos = binary_writer.tell()
        data_offset = 4 + len(value.files) * (256 + 4 * 3)
        binary_writer.seek(data_offset)

        entries = []
        for name, data in value.files.items():
            compressed_data = zlib.compress(data, level=9)

            offset = binary_writer.tell() - data_offset
            compressed_size = len(compressed_data)
            decompressed_size = len(data)

            binary_writer.write(compressed_data)

            entries.append(DBFEntry(name, offset, compressed_size, decompressed_size))

        binary_writer.seek(entries_pos)
        binary_writer.write_list(entries, DBFEntry.binwrite, None, endianness)


@dataclass
class NPCEntry(BinRead):
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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "NPCEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_fixed_size_string(value.name, 64)
        binary_writer.write_u32(value.compressed_size, endianness)
        binary_writer.write_u32(value.offset, endianness)
        binary_writer.write_u32(value.decompressed_size, endianness)


@dataclass
class NPC(BinRead, BinWrite):
    files: dict[str, bytes]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "NPC":
        num_entries = binary_reader.read_u32(endianness)

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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "NPC",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.files), endianness)

        entries_pos = binary_writer.tell()
        data_offset = 4 + len(value.files) * (64 + 4 * 3)
        binary_writer.seek(data_offset)

        entries = []
        for name, data in value.files.items():
            offset = binary_writer.tell() - data_offset
            compressed_size = 0
            decompressed_size = len(data)

            binary_writer.write(data)

            entries.append(NPCEntry(name, compressed_size, offset, decompressed_size))

        binary_writer.seek(entries_pos)
        binary_writer.write_list(entries, NPCEntry.binwrite, None, endianness)


@dataclass
class PCGData(BinRead):
    a: int
    b: int
    width: int
    height: int
    clip_width: int
    clip_height: int
    e: int
    f: int
    g: int
    h: int
    j: bytes
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: None, endianness: Endianness
    ) -> "PCGData":
        a = binary_reader.read_u32(endianness)
        b = binary_reader.read_u32(endianness)
        width = binary_reader.read_u32(endianness)
        height = binary_reader.read_u32(endianness)
        clip_width = binary_reader.read_u32(endianness)
        clip_height = binary_reader.read_u32(endianness)
        e = binary_reader.read_u32(endianness)
        f = binary_reader.read_u32(endianness)
        g = binary_reader.read_u32(endianness)
        h = binary_reader.read_u32(endianness)
        size = binary_reader.read_u32(endianness)
        j = binary_reader.read(84)
        data = binary_reader.read(size)
        return PCGData(
            a, b, width, height, clip_width, clip_height, e, f, g, h, j, data
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PCGData",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.a, endianness)
        binary_writer.write_u32(value.b, endianness)
        binary_writer.write_u32(value.width, endianness)
        binary_writer.write_u32(value.height, endianness)
        binary_writer.write_u32(value.clip_width, endianness)
        binary_writer.write_u32(value.clip_height, endianness)
        binary_writer.write_u32(value.e, endianness)
        binary_writer.write_u32(value.f, endianness)
        binary_writer.write_u32(value.g, endianness)
        binary_writer.write_u32(value.h, endianness)
        binary_writer.write_u32(len(value.data), endianness)
        assert len(value.j) == 84
        binary_writer.write(value.j)
        binary_writer.write(value.data)


@dataclass
class PCGEntry(BinRead, BinWrite):
    name: str
    data: PCGData

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: tuple[int], endianness: Endianness
    ) -> "PCGEntry":
        (num_entries,) = args
        offset = binary_reader.read_u32(endianness)
        name = binary_reader.read_fixed_size_string(0xC)
        pos = binary_reader.tell()
        binary_reader.seek(align_to(0x80, 0x10 + num_entries * 0x10) + offset)
        data = PCGData.binread(binary_reader, None, endianness)
        binary_reader.seek(pos)
        return PCGEntry(name, data)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PCGEntry",
        args: tuple[int],
        endianness: Endianness,
    ) -> None:
        (num_entries,) = args
        end_of_header = align_to(0x80, 0x10 + num_entries * 0x10)
        entry_pos = binary_writer.tell()
        binary_writer.seek(0, os.SEEK_END)
        if binary_writer.tell() < end_of_header:
            binary_writer.seek(end_of_header)
        offset = binary_writer.tell() - end_of_header
        PCGData.binwrite(binary_writer, value.data, None, endianness)
        binary_writer.seek(entry_pos)
        binary_writer.write_u32(offset, endianness)
        binary_writer.write_fixed_size_string(value.name, 0xC)


@dataclass
class PCG(BinRead, BinWrite):
    year_maybe: int
    checksum_or_time: int
    a: int
    entries: list[PCGEntry]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "PCG":
        num_entries = binary_reader.read_u32(endianness)
        year_maybe = binary_reader.read_u32(endianness)
        checksum_or_time = binary_reader.read_u32(endianness)
        a = binary_reader.read_u32(endianness)
        entries = binary_reader.read_list(
            num_entries, PCGEntry.binread, (num_entries,), endianness
        )
        return PCG(year_maybe, checksum_or_time, a, entries)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PCG",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.entries), endianness)  # num_entries
        binary_writer.write_u32(value.year_maybe, endianness)  # year_maybe
        binary_writer.write_u32(value.checksum_or_time, endianness)  # checksum_or_time
        binary_writer.write_u32(value.a, endianness)  # a
        binary_writer.write_list(
            value.entries, PCGEntry.binwrite, (len(value.entries),), endianness
        )


# TODO: Why can't I use BinWrite/BinRead here?
class DDSPixelFormatFourCC(StrEnum):
    NONE = "\0\0\0\0"
    BC1 = "DXT1"
    BC2 = "DXT3"

    @classmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: None, endianness: Endianness
    ) -> "DDSPixelFormatFourCC":
        return DDSPixelFormatFourCC(binary_reader.read_fixed_size_string(4))

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DDSPixelFormatFourCC",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_string(value)


@dataclass
class DDSPixelFormat(BinWrite, BinRead):
    flags: int
    fourCC: DDSPixelFormatFourCC
    RGBBitCount: int
    rBitMask: int
    gBitMask: int
    bBitMask: int
    aBitMask: int

    @classmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: None, endianness: Endianness
    ) -> "DDSPixelFormat":
        ddspf_size = binary_reader.read_u32(endianness)
        assert ddspf_size == 0x20
        flags = binary_reader.read_u32(endianness)
        fourCC = DDSPixelFormatFourCC.binread(binary_reader, None, endianness)
        RGBBitCount = binary_reader.read_u32(endianness)
        rBitMask = binary_reader.read_u32(endianness)
        gBitMask = binary_reader.read_u32(endianness)
        bBitMask = binary_reader.read_u32(endianness)
        aBitMask = binary_reader.read_u32(endianness)
        return DDSPixelFormat(
            flags, fourCC, RGBBitCount, rBitMask, gBitMask, bBitMask, aBitMask
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DDSPixelFormat",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(0x20, endianness)  # size
        binary_writer.write_u32(value.flags, endianness)  # flags
        DDSPixelFormatFourCC.binwrite(
            binary_writer, value.fourCC, None, endianness
        )  # fourCC
        binary_writer.write_u32(value.RGBBitCount, endianness)  # RGBBitCount
        binary_writer.write_u32(value.rBitMask, endianness)  # rBitMask
        binary_writer.write_u32(value.gBitMask, endianness)  # gBitMask
        binary_writer.write_u32(value.bBitMask, endianness)  # bBitMask
        binary_writer.write_u32(value.aBitMask, endianness)  # aBitMask

    @staticmethod
    def from_bc1() -> "DDSPixelFormat":
        return DDSPixelFormat(0x4, DDSPixelFormatFourCC.BC1, 0, 0, 0, 0, 0)

    @staticmethod
    def from_bc2() -> "DDSPixelFormat":
        return DDSPixelFormat(0x4, DDSPixelFormatFourCC.BC2, 0, 0, 0, 0, 0)

    @staticmethod
    def from_rgba() -> "DDSPixelFormat":
        return DDSPixelFormat(
            0x41,
            DDSPixelFormatFourCC.NONE,
            32,
            0x000000FF,
            0x0000FF00,
            0x00FF0000,
            0xFF000000,
        )

    @staticmethod
    def from_rgb() -> "DDSPixelFormat":
        return DDSPixelFormat(
            0x40, DDSPixelFormatFourCC.NONE, 24, 0x00FF0000, 0x0000FF00, 0x000000FF, 0
        )

    def get_bytes_per_pixel(self) -> float:
        match self.fourCC:
            case DDSPixelFormatFourCC.BC1:
                return 0.5
            case DDSPixelFormatFourCC.BC2:
                return 1
            case DDSPixelFormatFourCC.NONE:
                return self.RGBBitCount // 8

    def is_compressed(self):
        return self.fourCC != DDSPixelFormatFourCC.NONE


class DDSFlags:
    DDSD_CAPS: int = 0x1
    DDSD_HEIGHT: int = 0x2
    DDSD_WIDTH: int = 0x4
    DDSD_PITCH: int = 0x8
    DDSD_PIXELFORMAT: int = 0x1000
    DDSD_MIPMAPCOUNT: int = 0x20000
    DDSD_LINEARSIZE: int = 0x80000
    DDSD_DEPTH: int = 0x800000


@dataclass
class DDSHeader(BinWrite, BinRead):
    width: int
    height: int
    mip_map_count: int
    ddspf: DDSPixelFormat

    @classmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: None, endianness: Endianness
    ) -> "DDSHeader":
        id = binary_reader.read_fixed_size_string(4)
        assert id == "DDS "
        size = binary_reader.read_u32(endianness)
        assert size == 0x7C
        flags = binary_reader.read_u32(endianness)
        height = binary_reader.read_u32(endianness)
        width = binary_reader.read_u32(endianness)
        pitchOrLinearSize = binary_reader.read_u32(endianness)
        depth = binary_reader.read_u32(endianness)
        mipMapCount = binary_reader.read_u32(endianness)
        reserved0 = binary_reader.read(44)
        ddspf = DDSPixelFormat.binread(binary_reader, None, endianness)
        caps = binary_reader.read_u32(endianness)
        caps2 = binary_reader.read_u32(endianness)
        caps3 = binary_reader.read_u32(endianness)
        caps4 = binary_reader.read_u32(endianness)
        reserved1 = binary_reader.read_u32(endianness)
        return DDSHeader(width, height, mipMapCount, ddspf)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DDSHeader",
        args: None,
        endianness: Endianness,
    ) -> None:
        flags = (
            DDSFlags.DDSD_CAPS
            | DDSFlags.DDSD_HEIGHT
            | DDSFlags.DDSD_WIDTH
            | DDSFlags.DDSD_PIXELFORMAT
            | DDSFlags.DDSD_MIPMAPCOUNT
        )
        if value.ddspf.is_compressed():
            flags |= DDSFlags.DDSD_LINEARSIZE
            pitchOrLinearSize = int(
                value.width * value.height * value.ddspf.get_bytes_per_pixel()
            )
        else:
            flags |= DDSFlags.DDSD_PITCH
            pitchOrLinearSize = int(value.width * value.ddspf.get_bytes_per_pixel())

        binary_writer.write_string("DDS ")  # id
        binary_writer.write_u32(0x7C, endianness)  # size
        binary_writer.write_u32(flags, endianness)  # flags
        binary_writer.write_u32(value.height, endianness)  # height
        binary_writer.write_u32(value.width, endianness)  # width
        binary_writer.write_u32(pitchOrLinearSize, endianness)  # pitchOrLinearSize
        binary_writer.write_u32(1, endianness)  # depth
        binary_writer.write_u32(value.mip_map_count, endianness)  # mipMapCount
        binary_writer.write(b"\0" * 44)  # reserved0
        DDSPixelFormat.binwrite(binary_writer, value.ddspf, None, endianness)
        binary_writer.write_u32(0x00401008, endianness)  # caps
        binary_writer.write_u32(0, endianness)  # caps2
        binary_writer.write_u32(0, endianness)  # caps3
        binary_writer.write_u32(0, endianness)  # caps4
        binary_writer.write_u32(0, endianness)  # reserved1


@dataclass
class TexturesPcEntry(BinRead):
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TexturesPcEntry":
        data = binary_reader.read(0x400)
        return TexturesPcEntry(data)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TexturesPcEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.data) == 0x400
        binary_writer.write(value.data)


@dataclass
class TexturesPcEntry2(BinRead):
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TexturesPcEntry2":
        data = binary_reader.read(0x40)
        return TexturesPcEntry2(data)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TexturesPcEntry2",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.data) == 0x40
        binary_writer.write(value.data)


@dataclass
class TexturesPcEntry3(BinRead):
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TexturesPcEntry3":
        data = binary_reader.read(0x400)
        return TexturesPcEntry3(data)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TexturesPcEntry3",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.data) == 0x400
        binary_writer.write(value.data)


def calculate_dds_data_size_internal(
    width: int, height: int, ddspf: DDSPixelFormat
) -> int:
    return int(width * height * ddspf.get_bytes_per_pixel())


def calculate_dds_data_size(
    width: int, height: int, num_mipmaps: int, ddspf: DDSPixelFormat
) -> int:
    size = 0
    calculated_num_mipmaps = 0

    size += calculate_dds_data_size_internal(width, height, ddspf)
    width >>= 1
    height >>= 1
    while width >= 4 and height >= 4 and num_mipmaps != 0:
        size += calculate_dds_data_size_internal(width, height, ddspf)
        width >>= 1
        height >>= 1
        calculated_num_mipmaps += 1
    assert calculated_num_mipmaps == num_mipmaps
    return size


@dataclass
class TexturesPcEntry4(BinRead):
    flags: int
    b: int
    name: str
    encoding: int
    num_mipmaps: int
    e: float
    width: int
    height: int
    h: int
    i: int
    j: int
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TexturesPcEntry4":
        flags = binary_reader.read_u32(endianness)
        b = binary_reader.read_u32(endianness)
        name_size = binary_reader.read_u32(endianness)
        name = binary_reader.read_fixed_size_string(name_size)
        encoding = binary_reader.read_u32(endianness)
        num_mipmaps = binary_reader.read_u32(endianness)
        e = binary_reader.read_float(endianness)
        width = binary_reader.read_u32(endianness)
        height = binary_reader.read_u32(endianness)
        h = binary_reader.read_u32(endianness)
        i = binary_reader.read_s32(endianness)
        j = binary_reader.read_s32(endianness)
        data = binary_reader.read(
            calculate_dds_data_size(
                width,
                height,
                num_mipmaps,
                TexturesPcEntry4.get_dds_pixel_format_from_encoding_and_flags(
                    encoding, flags
                ),
            )
        )
        return TexturesPcEntry4(
            flags, b, name, encoding, num_mipmaps, e, width, height, h, i, j, data
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TexturesPcEntry4",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.flags, endianness)
        binary_writer.write_u32(value.b, endianness)
        binary_writer.write_u32(len(value.name) + 1, endianness)
        binary_writer.write_fixed_size_string(value.name, len(value.name) + 1)
        binary_writer.write_u32(value.encoding, endianness)
        binary_writer.write_u32(value.num_mipmaps, endianness)
        binary_writer.write_float(value.e, endianness)
        binary_writer.write_u32(value.width, endianness)
        binary_writer.write_u32(value.height, endianness)
        binary_writer.write_u32(value.h, endianness)
        binary_writer.write_s32(value.i, endianness)
        binary_writer.write_s32(value.j, endianness)

        assert len(value.data) == calculate_dds_data_size(
            value.width,
            value.height,
            value.num_mipmaps,
            value.get_dds_pixel_format(),
        )
        binary_writer.write(value.data)

    @staticmethod
    def get_dds_pixel_format_from_encoding_and_flags(
        encoding: int, flags: int
    ) -> DDSPixelFormat:
        if encoding == 1:
            encoding = 5
        if (flags & 0x10) != 0:
            match encoding:
                case 2 | 3:
                    return DDSPixelFormat.from_rgba()
                case 5:
                    return DDSPixelFormat.from_rgb()
        else:
            match encoding:
                case 2 | 5:
                    return DDSPixelFormat.from_bc1()
                case 3:
                    return DDSPixelFormat.from_bc2()
        assert False

    def get_dds_pixel_format(self) -> DDSPixelFormat:
        return TexturesPcEntry4.get_dds_pixel_format_from_encoding_and_flags(
            self.encoding, self.flags
        )


@dataclass
class TexturesPc(BinRead, BinWrite):
    entries: list[TexturesPcEntry]
    entries2: list[TexturesPcEntry2]
    entries3: list[TexturesPcEntry3]
    b: int
    entries4: list[TexturesPcEntry4]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TexturesPc":
        num_entries = binary_reader.read_u32(endianness)
        num_entries2 = binary_reader.read_u32(endianness)
        num_entries3 = binary_reader.read_u32(endianness)
        entries = binary_reader.read_list(
            num_entries, TexturesPcEntry.binread, None, endianness
        )
        entries2 = binary_reader.read_list(
            num_entries2, TexturesPcEntry2.binread, None, endianness
        )
        entries3 = binary_reader.read_list(
            num_entries3, TexturesPcEntry3.binread, None, endianness
        )
        num_entries4 = binary_reader.read_u32(endianness)
        b = binary_reader.read_u32(endianness)
        entries4 = binary_reader.read_list(
            num_entries4, TexturesPcEntry4.binread, None, endianness
        )
        return TexturesPc(entries, entries2, entries3, b, entries4)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TexturesPc",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.entries), endianness)
        binary_writer.write_u32(len(value.entries2), endianness)
        binary_writer.write_u32(len(value.entries3), endianness)
        binary_writer.write_list(
            value.entries, TexturesPcEntry.binwrite, None, endianness
        )
        binary_writer.write_list(
            value.entries2, TexturesPcEntry2.binwrite, None, endianness
        )
        binary_writer.write_list(
            value.entries3, TexturesPcEntry3.binwrite, None, endianness
        )
        binary_writer.write_u32(len(value.entries4), endianness)
        binary_writer.write_u32(value.b, endianness)
        binary_writer.write_list(
            value.entries4, TexturesPcEntry4.binwrite, None, endianness
        )
