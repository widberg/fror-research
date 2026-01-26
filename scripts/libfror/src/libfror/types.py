from enum import ReprEnum
import os
from io import BytesIO
import typing
from .binrw import BinWrite, BinaryReader, BinaryWriter, Endianness, BinRead, align_to
from dataclasses import dataclass
import zlib
from pathlib import Path
from .compression import get_decompressed_binary_reader_from_path


@dataclass
class FileFormat:
    name: str
    glob: str
    compressed: bool


DBF_FILE_FORMAT = FileFormat("dbf", "data/**/*.dbf", False)
BININFO_BIN_FILE_FORMAT = FileFormat("bininfo_bin", "data/**/bininfo.bin", False)
FONTS_HDR_FILE_FORMAT = FileFormat("fonts_hdr", "data/**/fonts.hdr", False)
FONTS_RAW_FILE_FORMAT = FileFormat("fonts_raw", "data/**/fonts/*.raw", False)
FONTS_DAT_FILE_FORMAT = FileFormat("fonts_dat", "data/**/fonts.dat", False)
GRADIENT_DAT_FILE_FORMAT = FileFormat("gradient_dat", "data/**/gradient.dat", False)
NPC_FILE_FORMAT = FileFormat("npc", "data/**/*.npc", False)
PCG_FILE_FORMAT = FileFormat("pcg", "data/**/*.pcg", True)
PVS_FILE_FORMAT = FileFormat("pvs", "data/**/*.pvs", True)
SPC_FILE_FORMAT = FileFormat("spc", "data/**/*.spc", False)
TEXTURES_PC_FILE_FORMAT = FileFormat("textures_pc", "data/**/textures.pc", True)
THREE_D_OBJ_DB_PC_FILE_FORMAT = FileFormat("3dobjdb_pc", "data/**/3dobjdb.pc", False)
THREE_D_OBJS_PC_FILE_FORMAT = FileFormat("3dobjs_pc", "data/**/3dobjs.pc", True)
THREE_D_OBJSP_PC_FILE_FORMAT = FileFormat("3dobjsp_pc", "data/**/3dobjsp.pc", True)


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
    num_triangle_strips: int
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "MeshDescriptor":
        flags = binary_reader.read_u32(endianness)
        w = binary_reader.read_s16(endianness)
        num_vertices = binary_reader.read_u16(endianness)
        num_triangle_strips = binary_reader.read_u16(endianness)
        data = binary_reader.read(calculate_size(flags, w) - 4 - 2 - 2 - 2)
        return MeshDescriptor(flags, w, num_vertices, num_triangle_strips, data)


@dataclass
class TriangleStrip(BinRead):
    indices: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "TriangleStrip":
        num_indices = binary_reader.read_u16(endianness)
        indices = binary_reader.read_list(
            num_indices, BinaryReader.read_u16_args, None, endianness
        )
        return TriangleStrip(indices)


@dataclass
class TriangleStripBuffer(BinRead):
    triangle_strips: list[TriangleStrip]

    @classmethod
    def binread(
        cls,
        binary_reader: BinaryReader,
        args: MeshDescriptor,
        endianness: Endianness,
    ) -> "TriangleStripBuffer":
        mesh_descriptor = args
        triangle_strips = binary_reader.read_list(
            mesh_descriptor.num_triangle_strips, TriangleStrip.binread, None, endianness
        )
        return TriangleStripBuffer(triangle_strips)


@dataclass
class ThreeDObjsPc(BinRead):
    entries: list[ThreeDObjsPcEntry]
    mesh_descriptors: list[MeshDescriptor]
    triangle_strip_buffers: list[TriangleStripBuffer]

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
        triangle_strip_buffers = binary_reader.read_list_iter(
            mesh_descriptors, TriangleStripBuffer.binread, endianness
        )
        return ThreeDObjsPc(entries, mesh_descriptors, triangle_strip_buffers)


def read_u16_float(binary_reader: BinaryReader, args: None, endianness: Endianness):
    value = binary_reader.read_s16(endianness)
    return float(value) / 0x800


@dataclass
class VertexBuffer(BinRead):
    positions: list[tuple[float, float, float]]
    uvs: list[tuple[float, float]]
    uvs2: typing.Optional[list[tuple[float, float]]]

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
        uvs2 = None
        if w >= 0:
            uvs2 = binary_reader.read_list(
                num_vertices,
                lambda b, a, e: BinaryReader.read_tuple_2(b, read_u16_float, a, e),
                None,
                endianness,
            )
        return VertexBuffer(positions, uvs, uvs2)


@dataclass
class DBFEntry(BinRead):
    name: str
    offset: int
    compressed_size: int
    decompressed_size: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "DBFEntry":
        name = binary_reader.read_fixed_size_null_terminated_string(256)
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
    flags: int
    offset: int
    size: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "NPCEntry":
        name = binary_reader.read_fixed_size_null_terminated_string(64)
        flags = binary_reader.read_u32(endianness)
        offset = binary_reader.read_u32(endianness)
        size = binary_reader.read_u32(endianness)
        return NPCEntry(name, flags, offset, size)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "NPCEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_fixed_size_string(value.name, 64)
        binary_writer.write_u32(value.flags, endianness)
        binary_writer.write_u32(value.offset, endianness)
        binary_writer.write_u32(value.size, endianness)


@dataclass
class NPCFile:
    flags: int
    data: bytes


@dataclass
class NPC(BinRead, BinWrite):
    files: dict[str, NPCFile]

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

        files: dict[str, NPCFile] = {}

        for entry in entries:
            binary_reader.seek(data_offset + entry.offset)
            data = binary_reader.read(entry.size)

            assert entry.name not in files
            files[entry.name] = NPCFile(entry.flags, data)

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
        for name, file in value.files.items():
            offset = binary_writer.tell() - data_offset
            size = len(file.data)

            binary_writer.write(file.data)

            entries.append(NPCEntry(name, file.flags, offset, size))

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
        name = binary_reader.read_fixed_size_null_terminated_string(0xC)
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


class BytesEnum(bytes, ReprEnum):
    def __new__(cls, value: bytes) -> "BytesEnum":
        if not isinstance(value, (bytes,)):
            raise TypeError("BytesEnum values must be bytes")
        return bytes.__new__(cls, value)


# EnumMeta conflicts with Protocol/ABCMeta, so we can't inherit from BinRead/BinWrite.
class DDSPixelFormatFourCC(BytesEnum):
    NONE = b"\0\0\0\0"
    BC1 = b"DXT1"
    BC2 = b"DXT3"

    @classmethod
    def binread(
        cls, binary_reader: "BinaryReader", args: None, endianness: Endianness
    ) -> "DDSPixelFormatFourCC":
        return DDSPixelFormatFourCC(binary_reader.read(4))

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "DDSPixelFormatFourCC",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value) == 4
        binary_writer.write(value)


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
        id = binary_reader.read_fixed_size_null_terminated_string(4)
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
class TexturesPcEntry(BinRead, BinWrite):
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
class TexturesPcEntry2(BinRead, BinWrite):
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
class TexturesPcEntry3(BinRead, BinWrite):
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
class TexturesPcEntry4(BinRead, BinWrite):
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
        name = binary_reader.read_fixed_size_null_terminated_string(name_size)
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
        binary_writer.write_null_terminated_string(value.name)
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

    def to_dds(self) -> bytes:
        bytes_io = BytesIO()
        binary_writer = BinaryWriter(bytes_io)
        dds_header = DDSHeader(
            self.width,
            self.height,
            self.num_mipmaps + 1,
            self.get_dds_pixel_format(),
        )
        DDSHeader.binwrite(binary_writer, dds_header, None, Endianness.LITTLE)
        binary_writer.write(self.data)
        return bytes_io.getvalue()

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


@dataclass
class BininfoBin(BinRead, BinWrite):
    groups: list[list[str]]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "BininfoBin":
        groups = []
        size = binary_reader.read_u32(endianness)
        for _ in range(12):
            strings = []
            num_strings = binary_reader.read_u32(endianness)
            for _ in range(num_strings):
                offset = binary_reader.read_u32(endianness)
                pos = binary_reader.tell()
                binary_reader.seek(offset)
                string = binary_reader.read_null_terminated_string()
                binary_reader.seek(pos)
                strings.append(string)
            groups.append(strings)
        return BininfoBin(groups)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "BininfoBin",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.groups) == 12
        end_of_header = (
            4 + 4 * len(value.groups) + 4 * sum(len(x) for x in value.groups)
        )
        binary_writer.write_u32(0, endianness)
        for group in value.groups:
            binary_writer.write_u32(len(group), endianness)  # num_strings
            for string in group:
                pos = binary_writer.tell()
                binary_writer.seek(0, os.SEEK_END)
                if binary_writer.tell() < end_of_header:
                    binary_writer.seek(end_of_header)
                offset = binary_writer.tell()
                binary_writer.write_null_terminated_string(string)
                binary_writer.seek(pos)
                binary_writer.write_u32(offset, endianness)
        binary_writer.seek(0, os.SEEK_END)
        size = binary_writer.tell()
        binary_writer.seek(0)
        binary_writer.write_u32(size, endianness)  # size


@dataclass
class ThreeDObjPc:
    three_d_obj_db_pc: bytes  # TODO: Real ThreeDObjDBPc type
    three_d_objs_pc: ThreeDObjsPc
    three_d_objsp_pc: list[VertexBuffer]
    bininfo_bin: BininfoBin
    textures_pc: TexturesPc

    @classmethod
    def from_directory_path(cls, path: Path, endianness: Endianness) -> "ThreeDObjPc":
        three_d_obj_db_pc_path = path / "3dobjdb.pc"
        three_d_objs_pc_path = path / "3dobjs.pc"
        three_d_objsp_pc_path = path / "3dobjsp.pc"
        bininfo_bin_path = path / "bininfo.bin"
        textures_pc_path = path / "textures.pc"

        # three_d_obj_db_pc
        three_d_obj_db_pc = three_d_obj_db_pc_path.read_bytes()

        # three_d_objs_pc
        three_d_objs_pc_binary_reader = get_decompressed_binary_reader_from_path(
            three_d_objs_pc_path
        )
        three_d_objs_pc = ThreeDObjsPc.binread(
            three_d_objs_pc_binary_reader,
            None,
            endianness,
        )
        assert len(three_d_objs_pc_binary_reader.read()) == 0

        # three_d_objsp_pc
        three_d_objsp_pc_binary_reader = get_decompressed_binary_reader_from_path(
            three_d_objsp_pc_path
        )
        three_d_objsp_pc = three_d_objsp_pc_binary_reader.read_list_iter(
            map(lambda m: (m.num_vertices, m.w), three_d_objs_pc.mesh_descriptors),
            VertexBuffer.binread,
            endianness,
        )
        assert len(three_d_objsp_pc_binary_reader.read()) == 0

        # bininfo_bin
        with open(bininfo_bin_path, "rb") as f:
            bininfo_bin_binary_reader = BinaryReader(f)
            bininfo_bin = BininfoBin.binread(
                bininfo_bin_binary_reader, None, endianness
            )

        # textures_pc
        textures_pc_binary_reader = get_decompressed_binary_reader_from_path(
            textures_pc_path
        )
        textures_pc = TexturesPc.binread(textures_pc_binary_reader, None, endianness)
        assert len(textures_pc_binary_reader.read()) == 0

        return ThreeDObjPc(
            three_d_obj_db_pc,
            three_d_objs_pc,
            three_d_objsp_pc,
            bininfo_bin,
            textures_pc,
        )
