import os
import typing
import zlib
from dataclasses import dataclass
from enum import ReprEnum
from io import BytesIO
from pathlib import Path

from .binrw import (
    BinaryReader,
    BinaryWriter,
    BinRead,
    BinWrite,
    Endianness,
    align_to,
)


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
class ObjectThing(BinRead, BinWrite):
    length: int
    flags: int
    n: int
    begin: int
    p: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ObjectThing":
        length = binary_reader.read_u16(endianness)
        flags = binary_reader.read_u16(endianness)
        n = binary_reader.read_u32(endianness)
        begin = binary_reader.read_u32(endianness)
        p = binary_reader.read_u32(endianness)
        return ObjectThing(length, flags, n, begin, p)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ObjectThing",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u16(value.length, endianness)
        binary_writer.write_u16(value.flags, endianness)
        binary_writer.write_u32(value.n, endianness)
        binary_writer.write_u32(value.begin, endianness)
        binary_writer.write_u32(value.p, endianness)


@dataclass
class ThreeDObjsPcEntry(BinRead, BinWrite):
    transformation: list[float]
    lod_near: ObjectThing
    lod_far: ObjectThing
    u: int
    v: int
    w: float
    x: float

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjsPcEntry":
        transformation = binary_reader.read_list(
            12, BinaryReader.read_float_args, None, endianness
        )
        lod_near = ObjectThing.binread(binary_reader, None, endianness)
        lod_far = ObjectThing.binread(binary_reader, None, endianness)
        u = binary_reader.read_u32(endianness)
        v = binary_reader.read_u32(endianness)
        w = binary_reader.read_float(endianness)
        x = binary_reader.read_float(endianness)
        return ThreeDObjsPcEntry(transformation, lod_near, lod_far, u, v, w, x)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjsPcEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_list(
            value.transformation, BinaryWriter.write_float_args, None, endianness
        )
        ObjectThing.binwrite(binary_writer, value.lod_near, None, endianness)
        ObjectThing.binwrite(binary_writer, value.lod_far, None, endianness)
        binary_writer.write_u32(value.u, endianness)
        binary_writer.write_u32(value.v, endianness)
        binary_writer.write_float(value.w, endianness)
        binary_writer.write_float(value.x, endianness)


def calculate_sum(arr: list[ThreeDObjsPcEntry]) -> int:
    sum = 0
    for i in range(len(arr)):
        elm = arr[i]
        sum += elm.lod_near.length + elm.lod_far.length
    return sum


def calculate_size(flags: int, texture_index: int) -> int:
    size = 20
    cursor_0 = (flags >> 0) & 0xFF
    cursor_1 = (flags >> 8) & 0xFF
    cursor_2 = (flags >> 16) & 0xFF
    cursor_3 = (flags >> 24) & 0xFF
    if (cursor_1 & 8) != 0:
        size += 20
    if (cursor_1 & 1) != 0:
        size += 4
    if texture_index == -1 or (cursor_0 & 2) != 0 or (cursor_0 & 4) != 0:
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
class MeshDescriptor(BinRead, BinWrite):
    flags: int
    texture_index: int
    num_vertices: int
    num_triangle_strips: int
    data: bytes

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "MeshDescriptor":
        flags = binary_reader.read_u32(endianness)
        texture_index = binary_reader.read_s16(endianness)
        num_vertices = binary_reader.read_u16(endianness)
        num_triangle_strips = binary_reader.read_u16(endianness)
        data = binary_reader.read(calculate_size(flags, texture_index) - 4 - 2 - 2 - 2)
        return MeshDescriptor(
            flags, texture_index, num_vertices, num_triangle_strips, data
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "MeshDescriptor",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.flags, endianness)
        binary_writer.write_s16(value.texture_index, endianness)
        binary_writer.write_u16(value.num_vertices, endianness)
        binary_writer.write_u16(value.num_triangle_strips, endianness)
        expected_size = calculate_size(value.flags, value.texture_index) - 4 - 2 - 2 - 2
        assert len(value.data) == expected_size
        binary_writer.write(value.data)


@dataclass
class TriangleStrip(BinRead, BinWrite):
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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TriangleStrip",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.indices) <= 0xFFFF
        binary_writer.write_u16(len(value.indices), endianness)
        binary_writer.write_list(
            value.indices, BinaryWriter.write_u16_args, None, endianness
        )


@dataclass
class TriangleStripBuffer(BinRead, BinWrite):
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

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "TriangleStripBuffer",
        args: MeshDescriptor,
        endianness: Endianness,
    ) -> None:
        mesh_descriptor = args
        assert len(value.triangle_strips) == mesh_descriptor.num_triangle_strips
        binary_writer.write_list(
            value.triangle_strips, TriangleStrip.binwrite, None, endianness
        )

    def to_triangles_cw(self) -> list[list[int]]:
        triangles: list[list[int]] = []

        for current_strip in self.triangle_strips:
            indices = current_strip.indices
            assert len(indices) >= 3
            for i in range(2, len(indices)):
                if i % 2 == 0:
                    triangles.append([indices[i - 2], indices[i - 1], indices[i]])
                else:
                    triangles.append([indices[i - 1], indices[i - 2], indices[i]])

        return triangles

    def to_triangles_ccw(self) -> list[list[int]]:
        return [[a, c, b] for a, b, c in self.to_triangles_cw()]

    @classmethod
    def from_triangles_cw(cls, triangles: list[list[int]]) -> "TriangleStripBuffer":
        strips: list[TriangleStrip] = []

        for triangle in triangles:
            assert len(triangle) == 3

            if strips:
                current_strip = strips[-1]
                indices = current_strip.indices
                if (len(indices) - 2) % 2 == 0:
                    required_v0, required_v1 = indices[-2], indices[-1]
                else:
                    required_v0, required_v1 = indices[-1], indices[-2]
                if triangle[0] == required_v0 and triangle[1] == required_v1:
                    indices.append(triangle[2])
                    continue

            strips.append(TriangleStrip([triangle[0], triangle[1], triangle[2]]))

        return TriangleStripBuffer(strips)

    @classmethod
    def from_triangles_ccw(cls, triangles: list[list[int]]) -> "TriangleStripBuffer":
        return cls.from_triangles_cw([[a, c, b] for a, b, c in triangles])


@dataclass
class ThreeDObjsPc(BinRead, BinWrite):
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
            TriangleStripBuffer.binread, mesh_descriptors, endianness
        )
        return ThreeDObjsPc(entries, mesh_descriptors, triangle_strip_buffers)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjsPc",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.entries), endianness)
        binary_writer.write(b"\0" * 0xC)
        binary_writer.write_list(
            value.entries, ThreeDObjsPcEntry.binwrite, None, endianness
        )
        assert len(value.mesh_descriptors) == calculate_sum(value.entries)
        binary_writer.write_list(
            value.mesh_descriptors, MeshDescriptor.binwrite, None, endianness
        )
        assert len(value.triangle_strip_buffers) == len(value.mesh_descriptors)
        binary_writer.write_list_iter(
            value.triangle_strip_buffers,
            TriangleStripBuffer.binwrite,
            value.mesh_descriptors,
            endianness,
        )


def read_s16_float(binary_reader: BinaryReader, args: None, endianness: Endianness):
    value = binary_reader.read_s16(endianness)
    return float(value) / 0x800


def write_s16_float(
    binary_writer: BinaryWriter, value: float, args: None, endianness: Endianness
):
    packed = max(-0x8000, min(0x7FFF, round(value * 0x800)))
    binary_writer.write_s16(packed, endianness)


def read_s8_snorm_float(
    binary_reader: BinaryReader, args: None, endianness: Endianness
):
    value = binary_reader.read_s8(endianness)
    if value == -128:
        return -1.0
    return float(value) / 127.0


def write_s8_snorm_float(
    binary_writer: BinaryWriter, value: float, args: None, endianness: Endianness
):
    packed = max(-127, min(127, round(value * 127.0)))
    binary_writer.write_s8(packed, endianness)


def read_u8_unorm_float(
    binary_reader: BinaryReader, args: None, endianness: Endianness
):
    value = binary_reader.read_u8(endianness)
    return float(value) / 255.0


def write_u8_unorm_float(
    binary_writer: BinaryWriter, value: float, args: None, endianness: Endianness
):
    packed = max(0, min(255, round(value * 255.0)))
    binary_writer.write_u8(packed, endianness)


def read_packed_normal(
    binary_reader: BinaryReader, args: None, endianness: Endianness
) -> tuple[float, float, float]:
    x, y, z = BinaryReader.read_tuple_3(
        binary_reader, read_s8_snorm_float, None, endianness
    )
    w = binary_reader.read_u8(endianness)
    return (x, y, z)


def write_packed_normal(
    binary_writer: BinaryWriter,
    value: tuple[float, float, float],
    args: None,
    endianness: Endianness,
) -> None:
    binary_writer.write_tuple_3(value, write_s8_snorm_float, None, endianness)
    binary_writer.write_u8(0, endianness)


def read_packed_color(
    binary_reader: BinaryReader, args: None, endianness: Endianness
) -> tuple[float, float, float, float]:
    return BinaryReader.read_tuple_4(
        binary_reader, read_u8_unorm_float, None, endianness
    )


def write_packed_color(
    binary_writer: BinaryWriter,
    value: tuple[float, float, float, float],
    args: None,
    endianness: Endianness,
) -> None:
    binary_writer.write_tuple_4(value, write_u8_unorm_float, None, endianness)


@dataclass
class VertexNormals:
    normals: list[tuple[float, float, float]]


@dataclass
class VertexColors:
    colors: list[tuple[float, float, float, float]]


VertexNormalsOrColors: typing.TypeAlias = VertexNormals | VertexColors
VERTEX_NORMALS_OR_COLORS_MASK = 0x6000
VERTEX_NORMALS_MODE = 0x2000
VERTEX_COLORS_MODE = 0x4000


@dataclass
class VertexBuffer(BinRead, BinWrite):
    positions: list[tuple[float, float, float]]
    normals_or_colors: VertexNormalsOrColors
    uvs: typing.Optional[list[tuple[float, float]]]

    @classmethod
    def binread(
        cls,
        binary_reader: BinaryReader,
        args: MeshDescriptor,
        endianness: Endianness,
    ) -> "VertexBuffer":
        mesh_descriptor = args
        num_vertices = mesh_descriptor.num_vertices
        texture_index = mesh_descriptor.texture_index
        flags = mesh_descriptor.flags
        positions = binary_reader.read_list(
            num_vertices,
            lambda b, a, e: BinaryReader.read_tuple_3(
                b, BinaryReader.read_float_args, a, e
            ),
            None,
            endianness,
        )
        normals_or_colors_mode = flags & VERTEX_NORMALS_OR_COLORS_MASK
        if normals_or_colors_mode == VERTEX_NORMALS_MODE:
            normals = binary_reader.read_list(
                num_vertices,
                read_packed_normal,
                None,
                endianness,
            )
            normals_or_colors: VertexNormalsOrColors = VertexNormals(normals)
        else:
            assert normals_or_colors_mode == VERTEX_COLORS_MODE
            colors = binary_reader.read_list(
                num_vertices,
                read_packed_color,
                None,
                endianness,
            )
            normals_or_colors = VertexColors(colors)
        uvs = None
        if texture_index >= 0:
            uvs = binary_reader.read_list(
                num_vertices,
                lambda b, a, e: BinaryReader.read_tuple_2(b, read_s16_float, a, e),
                None,
                endianness,
            )
        return VertexBuffer(positions, normals_or_colors, uvs)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "VertexBuffer",
        args: MeshDescriptor,
        endianness: Endianness,
    ) -> None:
        mesh_descriptor = args
        num_vertices = mesh_descriptor.num_vertices
        texture_index = mesh_descriptor.texture_index
        flags = mesh_descriptor.flags
        assert len(value.positions) == num_vertices
        binary_writer.write_list(
            value.positions,
            lambda b, position, a, e: BinaryWriter.write_tuple_3(
                b, position, BinaryWriter.write_float_args, a, e
            ),
            None,
            endianness,
        )

        normals_or_colors_mode = flags & VERTEX_NORMALS_OR_COLORS_MASK
        if normals_or_colors_mode == VERTEX_NORMALS_MODE:
            assert isinstance(value.normals_or_colors, VertexNormals)
            assert len(value.normals_or_colors.normals) == num_vertices
            binary_writer.write_list(
                value.normals_or_colors.normals,
                write_packed_normal,
                None,
                endianness,
            )
        else:
            assert normals_or_colors_mode == VERTEX_COLORS_MODE
            assert isinstance(value.normals_or_colors, VertexColors)
            assert len(value.normals_or_colors.colors) == num_vertices
            binary_writer.write_list(
                value.normals_or_colors.colors,
                write_packed_color,
                None,
                endianness,
            )

        if texture_index >= 0:
            assert value.uvs is not None
            assert len(value.uvs) == num_vertices
            binary_writer.write_list(
                value.uvs,
                lambda b, uv, a, e: BinaryWriter.write_tuple_2(
                    b, uv, write_s16_float, a, e
                ),
                None,
                endianness,
            )
        else:
            assert value.uvs is None

    def positions_z_up(self) -> list[tuple[float, float, float]]:
        return self.to_z_up_v_up().positions

    def normals_or_colors_z_up(self) -> VertexNormalsOrColors:
        return self.to_z_up_v_up().normals_or_colors

    def uvs_v_up(self) -> typing.Optional[list[tuple[float, float]]]:
        return self.to_z_up_v_up().uvs

    def to_z_up_v_up(self) -> "VertexBuffer":
        return VertexBuffer(
            [y_up_to_z_up(position) for position in self.positions],
            normals_or_colors_y_up_to_z_up(self.normals_or_colors),
            None if self.uvs is None else [v_down_to_v_up(uv) for uv in self.uvs],
        )

    def to_y_up_v_down(self) -> "VertexBuffer":
        return VertexBuffer(
            [z_up_to_y_up(position) for position in self.positions],
            normals_or_colors_z_up_to_y_up(self.normals_or_colors),
            None if self.uvs is None else [v_up_to_v_down(uv) for uv in self.uvs],
        )

    @staticmethod
    def from_z_up_v_up(value: "VertexBuffer") -> "VertexBuffer":
        return value.to_y_up_v_down()

    @staticmethod
    def from_y_up_v_down(value: "VertexBuffer") -> "VertexBuffer":
        return value.to_z_up_v_up()


def y_up_to_z_up(position: tuple[float, float, float]) -> tuple[float, float, float]:
    return (position[0], position[2], position[1])


def z_up_to_y_up(position: tuple[float, float, float]) -> tuple[float, float, float]:
    return (position[0], position[2], position[1])


def v_down_to_v_up(uv: tuple[float, float]) -> tuple[float, float]:
    return (uv[0], 1 - uv[1])


def v_up_to_v_down(uv: tuple[float, float]) -> tuple[float, float]:
    return (uv[0], 1 - uv[1])


def normals_or_colors_y_up_to_z_up(
    normals_or_colors: VertexNormalsOrColors,
) -> VertexNormalsOrColors:
    match normals_or_colors:
        case VertexNormals(normals):
            return VertexNormals([y_up_to_z_up(normal) for normal in normals])
        case VertexColors() as colors:
            return colors


def normals_or_colors_z_up_to_y_up(
    normals_or_colors: VertexNormalsOrColors,
) -> VertexNormalsOrColors:
    match normals_or_colors:
        case VertexNormals(normals):
            return VertexNormals([z_up_to_y_up(normal) for normal in normals])
        case VertexColors() as colors:
            return colors


@dataclass
class ThreeDObjspPc(BinRead, BinWrite):
    vertex_buffers: list[VertexBuffer]

    @classmethod
    def binread(
        cls,
        binary_reader: BinaryReader,
        args: tuple[ThreeDObjsPc],
        endianness: Endianness,
    ) -> "ThreeDObjspPc":
        (three_d_objs_pc,) = args
        vertex_buffers = binary_reader.read_list_iter(
            VertexBuffer.binread,
            three_d_objs_pc.mesh_descriptors,
            endianness,
        )
        return ThreeDObjspPc(vertex_buffers)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjspPc",
        args: tuple[ThreeDObjsPc],
        endianness: Endianness,
    ) -> None:
        (three_d_objs_pc,) = args
        assert len(value.vertex_buffers) == len(three_d_objs_pc.mesh_descriptors)
        binary_writer.write_list_iter(
            value.vertex_buffers,
            VertexBuffer.binwrite,
            three_d_objs_pc.mesh_descriptors,
            endianness,
        )


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


@dataclass
class PVSVisibleSectorRecord(BinRead, BinWrite):
    visible_sector_x: int
    visible_sector_z: int
    packed_delta_x: int
    packed_delta_z: int
    visibility_flags: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "PVSVisibleSectorRecord":
        visible_sector_x = binary_reader.read_u8(endianness)
        visible_sector_z = binary_reader.read_u8(endianness)
        packed_delta_x = binary_reader.read_s8(endianness)
        packed_delta_z = binary_reader.read_s8(endianness)
        visibility_flags = binary_reader.read_u8(endianness)
        return PVSVisibleSectorRecord(
            visible_sector_x,
            visible_sector_z,
            packed_delta_x,
            packed_delta_z,
            visibility_flags,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PVSVisibleSectorRecord",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u8(value.visible_sector_x, endianness)
        binary_writer.write_u8(value.visible_sector_z, endianness)
        binary_writer.write_s8(value.packed_delta_x, endianness)
        binary_writer.write_s8(value.packed_delta_z, endianness)
        binary_writer.write_u8(value.visibility_flags, endianness)


@dataclass
class PVSSectorEntry(BinRead, BinWrite):
    sector_x: int
    sector_z: int
    sector_class: int
    reserved_metadata: bytes
    visible_sectors: list[PVSVisibleSectorRecord]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "PVSSectorEntry":
        sector_x = binary_reader.read_u32(endianness)
        sector_z = binary_reader.read_u32(endianness)
        sector_class = binary_reader.read_u32(endianness)
        reserved_metadata = binary_reader.read(0x1C)
        num_visible_sectors = binary_reader.read_u32(endianness)
        visible_sectors = binary_reader.read_list(
            num_visible_sectors, PVSVisibleSectorRecord.binread, None, endianness
        )
        alignment_padding = align_to(4, binary_reader.tell()) - binary_reader.tell()
        binary_reader.skip(alignment_padding)
        return PVSSectorEntry(
            sector_x,
            sector_z,
            sector_class,
            reserved_metadata,
            visible_sectors,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PVSSectorEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.reserved_metadata) == 0x1C
        binary_writer.write_u32(value.sector_x, endianness)
        binary_writer.write_u32(value.sector_z, endianness)
        binary_writer.write_u32(value.sector_class, endianness)
        binary_writer.write(value.reserved_metadata)
        binary_writer.write_u32(len(value.visible_sectors), endianness)
        binary_writer.write_list(
            value.visible_sectors, PVSVisibleSectorRecord.binwrite, None, endianness
        )
        alignment_padding = align_to(4, binary_writer.tell()) - binary_writer.tell()
        binary_writer.write(b"\0" * alignment_padding)


@dataclass
class PVS(BinRead, BinWrite):
    total_visible_sector_records: int
    sector_entries: list[PVSSectorEntry]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "PVS":
        num_sector_entries = binary_reader.read_u32(endianness)
        total_visible_sector_records = binary_reader.read_u32(endianness)
        sector_entries = binary_reader.read_list(
            num_sector_entries, PVSSectorEntry.binread, None, endianness
        )
        expected_total_visible_sector_records = sum(
            len(sector_entry.visible_sectors) for sector_entry in sector_entries
        )
        assert total_visible_sector_records == expected_total_visible_sector_records
        return PVS(total_visible_sector_records, sector_entries)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "PVS",
        args: None,
        endianness: Endianness,
    ) -> None:
        expected_total_visible_sector_records = sum(
            len(sector_entry.visible_sectors) for sector_entry in value.sector_entries
        )
        assert (
            value.total_visible_sector_records
            == expected_total_visible_sector_records
        )
        binary_writer.write_u32(len(value.sector_entries), endianness)
        binary_writer.write_u32(value.total_visible_sector_records, endianness)
        binary_writer.write_list(
            value.sector_entries, PVSSectorEntry.binwrite, None, endianness
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
    object_shape_names: list[str]
    sub_object_names: list[str]
    camera_names: list[str]
    texture_livery_sets: list[str]
    reserved4: list[str]
    scene_link_type_names: list[str]
    light_names: list[str]
    surface_or_zone_types: list[str]
    reserved8: list[str]
    effect_attachment_names: list[str]
    reserved10: list[str]
    damage_names: list[str]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "BininfoBin":
        def read_group() -> list[str]:
            strings = []
            num_strings = binary_reader.read_u32(endianness)
            for _ in range(num_strings):
                offset = binary_reader.read_u32(endianness)
                pos = binary_reader.tell()
                binary_reader.seek(offset)
                string = binary_reader.read_null_terminated_string()
                binary_reader.seek(pos)
                strings.append(string)
            return strings

        _size = binary_reader.read_u32(endianness)
        object_shape_names = read_group()
        sub_object_names = read_group()
        camera_names = read_group()
        texture_livery_sets = read_group()
        reserved4 = read_group()
        scene_link_type_names = read_group()
        light_names = read_group()
        surface_or_zone_types = read_group()
        reserved8 = read_group()
        effect_attachment_names = read_group()
        reserved10 = read_group()
        damage_names = read_group()
        return BininfoBin(
            object_shape_names=object_shape_names,
            sub_object_names=sub_object_names,
            camera_names=camera_names,
            texture_livery_sets=texture_livery_sets,
            reserved4=reserved4,
            scene_link_type_names=scene_link_type_names,
            light_names=light_names,
            surface_or_zone_types=surface_or_zone_types,
            reserved8=reserved8,
            effect_attachment_names=effect_attachment_names,
            reserved10=reserved10,
            damage_names=damage_names,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "BininfoBin",
        args: None,
        endianness: Endianness,
    ) -> None:
        string_groups = (
            value.object_shape_names,
            value.sub_object_names,
            value.camera_names,
            value.texture_livery_sets,
            value.reserved4,
            value.scene_link_type_names,
            value.light_names,
            value.surface_or_zone_types,
            value.reserved8,
            value.effect_attachment_names,
            value.reserved10,
            value.damage_names,
        )
        end_of_header = (
            4 + 4 * len(string_groups) + 4 * sum(len(group) for group in string_groups)
        )
        binary_writer.write_u32(0, endianness)
        for group in string_groups:
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


THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY = 0x01
THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_02 = 0x02
THREE_D_OBJ_DB_PC_ENTRY_HAS_PIVOT_DATA = 0x04
THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_08 = 0x08
THREE_D_OBJ_DB_PC_ENTRY_HAS_FLAG10_ENTRIES = 0x10


@dataclass
class ThreeDObjDbPcEntryTransform(BinRead, BinWrite):
    floats: list[float]
    data: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryTransform":
        floats = binary_reader.read_list(
            15, BinaryReader.read_float_args, None, endianness
        )
        data = binary_reader.read_list(8, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryTransform(floats, data)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryTransform",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.floats) == 15
        assert len(value.data) == 8
        binary_writer.write_list(
            value.floats, BinaryWriter.write_float_args, None, endianness
        )
        binary_writer.write_list(
            value.data, BinaryWriter.write_u32_args, None, endianness
        )


@dataclass
class ThreeDObjDbPcEntryEntry2(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryEntry2":
        a = binary_reader.read_list(7, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryEntry2(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryEntry2",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 7
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntryEntry3(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryEntry3":
        a = binary_reader.read_list(3, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryEntry3(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryEntry3",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 3
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntryEntry4(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryEntry4":
        a = binary_reader.read_list(2, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryEntry4(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryEntry4",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 2
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntryEntry5(BinRead, BinWrite):
    a: int
    b: int
    c: int
    translation: tuple[float, float, float]
    g: float
    h: int
    i: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryEntry5":
        a = binary_reader.read_u32(endianness)
        b = binary_reader.read_u16(endianness)
        c = binary_reader.read_u16(endianness)
        translation = binary_reader.read_tuple_3(
            BinaryReader.read_float_args, None, endianness
        )
        g = binary_reader.read_float(endianness)
        h = binary_reader.read_u32(endianness)
        i = binary_reader.read_u32(endianness)
        return ThreeDObjDbPcEntryEntry5(a, b, c, translation, g, h, i)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryEntry5",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.a, endianness)
        binary_writer.write_u16(value.b, endianness)
        binary_writer.write_u16(value.c, endianness)
        binary_writer.write_tuple_3(
            value.translation, BinaryWriter.write_float_args, None, endianness
        )
        binary_writer.write_float(value.g, endianness)
        binary_writer.write_u32(value.h, endianness)
        binary_writer.write_u32(value.i, endianness)

    def translation_z_up(self) -> tuple[float, float, float]:
        return y_up_to_z_up(self.translation)


@dataclass
class ThreeDObjDbPcEntryPivotData(BinRead, BinWrite):
    a: list[float]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryPivotData":
        a = binary_reader.read_list(7, BinaryReader.read_float_args, None, endianness)
        return ThreeDObjDbPcEntryPivotData(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryPivotData",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 7
        binary_writer.write_list(
            value.a, BinaryWriter.write_float_args, None, endianness
        )


@dataclass
class ThreeDObjDbPcEntryFlag10Entry(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryFlag10Entry":
        a = binary_reader.read_list(5, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryFlag10Entry(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryFlag10Entry",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 5
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntryEntry10(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntryEntry10":
        a = binary_reader.read_list(2, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntryEntry10(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntryEntry10",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 2
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcSceneNodeSubObjectBinding(BinRead, BinWrite):
    sub_object_name_index: int
    scene_node_index: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcSceneNodeSubObjectBinding":
        sub_object_name_index = binary_reader.read_u32(endianness)
        scene_node_index = binary_reader.read_u32(endianness)
        return ThreeDObjDbPcSceneNodeSubObjectBinding(
            sub_object_name_index, scene_node_index
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcSceneNodeSubObjectBinding",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.sub_object_name_index, endianness)
        binary_writer.write_u32(value.scene_node_index, endianness)


@dataclass
class ThreeDObjDbPcSceneNode(BinRead, BinWrite):
    scene_node_index: int
    a: int
    translation: tuple[float, float, float]
    e: int
    f: int
    g: int
    sub_object_bindings: list[ThreeDObjDbPcSceneNodeSubObjectBinding]
    child_nodes: list["ThreeDObjDbPcSceneNode"]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: tuple[int], endianness: Endianness
    ) -> "ThreeDObjDbPcSceneNode":
        (flags,) = args
        scene_node_index = binary_reader.read_u32(endianness)
        if (flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) != 0:
            return ThreeDObjDbPcSceneNode(
                scene_node_index,
                0,
                (0.0, 0.0, 0.0),
                0,
                0,
                0,
                [],
                [],
            )

        a = binary_reader.read_u16(endianness)
        binary_reader.skip(2)
        translation = binary_reader.read_tuple_3(
            BinaryReader.read_float_args, None, endianness
        )
        e = binary_reader.read_u32(endianness)
        f = binary_reader.read_u32(endianness)
        g = binary_reader.read_u32(endianness)
        num_sub_object_bindings = binary_reader.read_u32(endianness)
        sub_object_bindings = binary_reader.read_list(
            num_sub_object_bindings,
            ThreeDObjDbPcSceneNodeSubObjectBinding.binread,
            None,
            endianness,
        )
        num_child_nodes = binary_reader.read_u32(endianness)
        child_nodes = binary_reader.read_list(
            num_child_nodes, ThreeDObjDbPcSceneNode.binread, (flags,), endianness
        )
        return ThreeDObjDbPcSceneNode(
            scene_node_index,
            a,
            translation,
            e,
            f,
            g,
            sub_object_bindings,
            child_nodes,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcSceneNode",
        args: tuple[int],
        endianness: Endianness,
    ) -> None:
        (flags,) = args
        binary_writer.write_u32(value.scene_node_index, endianness)
        if (flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) != 0:
            assert value.a == 0
            assert value.translation == (0.0, 0.0, 0.0)
            assert value.e == 0
            assert value.f == 0
            assert value.g == 0
            assert len(value.sub_object_bindings) == 0
            assert len(value.child_nodes) == 0
            return

        binary_writer.write_u16(value.a, endianness)
        binary_writer.write(b"\0" * 2)
        binary_writer.write_tuple_3(
            value.translation, BinaryWriter.write_float_args, None, endianness
        )
        binary_writer.write_u32(value.e, endianness)
        binary_writer.write_u32(value.f, endianness)
        binary_writer.write_u32(value.g, endianness)
        binary_writer.write_u32(len(value.sub_object_bindings), endianness)
        binary_writer.write_list(
            value.sub_object_bindings,
            ThreeDObjDbPcSceneNodeSubObjectBinding.binwrite,
            None,
            endianness,
        )
        binary_writer.write_u32(len(value.child_nodes), endianness)
        binary_writer.write_list(
            value.child_nodes, ThreeDObjDbPcSceneNode.binwrite, (flags,), endianness
        )

    def translation_z_up(self) -> tuple[float, float, float]:
        return y_up_to_z_up(self.translation)


@dataclass
class ThreeDObjDbPcEntry(BinRead, BinWrite):
    object_shape_name_index: int
    transforms: list[ThreeDObjDbPcEntryTransform]
    entries2: list[ThreeDObjDbPcEntryEntry2]
    entries3: list[ThreeDObjDbPcEntryEntry3]
    entries4: list[ThreeDObjDbPcEntryEntry4]
    entries5: list[ThreeDObjDbPcEntryEntry5]
    flags: int
    entries6: list[ThreeDObjDbPcEntryPivotData]
    entries7: list[ThreeDObjDbPcEntryFlag10Entry]
    lod_switch_distances: list[float]
    scene_node_count: int
    scene_node_capacity: int
    active_scene_node_indices: list[int]
    c: int
    d: int
    e: int
    entries10: list[ThreeDObjDbPcEntryEntry10]
    root_scene_nodes: list[ThreeDObjDbPcSceneNode]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry":
        check = binary_reader.read_list(4, BinaryReader.read_s32_args, None, endianness)
        assert all(value == -1 for value in check)
        object_shape_name_index = binary_reader.read_u32(endianness)
        num_transforms = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        transforms = binary_reader.read_list(
            num_transforms, ThreeDObjDbPcEntryTransform.binread, None, endianness
        )
        num_entries2 = binary_reader.read_u32(endianness)
        entries2 = binary_reader.read_list(
            num_entries2, ThreeDObjDbPcEntryEntry2.binread, None, endianness
        )
        num_entries3 = binary_reader.read_u32(endianness)
        entries3 = binary_reader.read_list(
            num_entries3, ThreeDObjDbPcEntryEntry3.binread, None, endianness
        )
        num_entries4 = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        entries4 = binary_reader.read_list(
            num_entries4, ThreeDObjDbPcEntryEntry4.binread, None, endianness
        )
        num_entries5 = binary_reader.read_u16(endianness)
        binary_reader.skip(2)
        entries5 = binary_reader.read_list(
            num_entries5, ThreeDObjDbPcEntryEntry5.binread, None, endianness
        )
        flags = binary_reader.read_u32(endianness)
        entries6: list[ThreeDObjDbPcEntryPivotData] = []
        if (flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_PIVOT_DATA) != 0:
            num_entries6 = binary_reader.read_u32(endianness)
            entries6 = binary_reader.read_list(
                num_entries6, ThreeDObjDbPcEntryPivotData.binread, None, endianness
            )
        entries7: list[ThreeDObjDbPcEntryFlag10Entry] = []
        if (flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_FLAG10_ENTRIES) != 0:
            num_entries7 = binary_reader.read_u32(endianness)
            entries7 = binary_reader.read_list(
                num_entries7, ThreeDObjDbPcEntryFlag10Entry.binread, None, endianness
            )
        assert (
            flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_02
        ) == 0, "Unsupported ThreeDObjDbPcEntry flag FIXME_FLAG_02"
        assert (
            flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_08
        ) == 0, "Unsupported ThreeDObjDbPcEntry flag FIXME_FLAG_08"
        num_lod_switch_distances = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        lod_switch_distances = binary_reader.read_list(
            num_lod_switch_distances, BinaryReader.read_float_args, None, endianness
        )
        scene_node_count = binary_reader.read_u32(endianness)
        scene_node_capacity = binary_reader.read_u32(endianness)
        num_active_scene_nodes = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        active_scene_node_indices = binary_reader.read_list(
            num_active_scene_nodes, BinaryReader.read_u32_args, None, endianness
        )
        c = binary_reader.read_u32(endianness)
        d = binary_reader.read_u16(endianness)
        binary_reader.skip(2)
        e = binary_reader.read_u16(endianness)
        binary_reader.skip(2)
        num_entries10 = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        entries10 = binary_reader.read_list(
            num_entries10, ThreeDObjDbPcEntryEntry10.binread, None, endianness
        )
        num_root_scene_nodes = binary_reader.read_u8(endianness)
        binary_reader.skip(3)
        root_scene_nodes = binary_reader.read_list(
            num_root_scene_nodes, ThreeDObjDbPcSceneNode.binread, (flags,), endianness
        )
        return ThreeDObjDbPcEntry(
            object_shape_name_index,
            transforms,
            entries2,
            entries3,
            entries4,
            entries5,
            flags,
            entries6,
            entries7,
            lod_switch_distances,
            scene_node_count,
            scene_node_capacity,
            active_scene_node_indices,
            c,
            d,
            e,
            entries10,
            root_scene_nodes,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_list(
            [-1] * 4, BinaryWriter.write_s32_args, None, endianness
        )
        binary_writer.write_u32(value.object_shape_name_index, endianness)

        assert len(value.transforms) <= 0xFF
        binary_writer.write_u8(len(value.transforms), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.transforms, ThreeDObjDbPcEntryTransform.binwrite, None, endianness
        )

        binary_writer.write_u32(len(value.entries2), endianness)
        binary_writer.write_list(
            value.entries2, ThreeDObjDbPcEntryEntry2.binwrite, None, endianness
        )

        binary_writer.write_u32(len(value.entries3), endianness)
        binary_writer.write_list(
            value.entries3, ThreeDObjDbPcEntryEntry3.binwrite, None, endianness
        )

        assert len(value.entries4) <= 0xFF
        binary_writer.write_u8(len(value.entries4), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.entries4, ThreeDObjDbPcEntryEntry4.binwrite, None, endianness
        )

        assert len(value.entries5) <= 0xFFFF
        binary_writer.write_u16(len(value.entries5), endianness)
        binary_writer.write(b"\0" * 2)
        binary_writer.write_list(
            value.entries5, ThreeDObjDbPcEntryEntry5.binwrite, None, endianness
        )

        binary_writer.write_u32(value.flags, endianness)
        if (value.flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_PIVOT_DATA) != 0:
            binary_writer.write_u32(len(value.entries6), endianness)
            binary_writer.write_list(
                value.entries6, ThreeDObjDbPcEntryPivotData.binwrite, None, endianness
            )
        else:
            assert len(value.entries6) == 0

        if (value.flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_FLAG10_ENTRIES) != 0:
            binary_writer.write_u32(len(value.entries7), endianness)
            binary_writer.write_list(
                value.entries7, ThreeDObjDbPcEntryFlag10Entry.binwrite, None, endianness
            )
        else:
            assert len(value.entries7) == 0

        assert (
            value.flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_02
        ) == 0, "Unsupported ThreeDObjDbPcEntry flag FIXME_FLAG_02"
        assert (
            value.flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_08
        ) == 0, "Unsupported ThreeDObjDbPcEntry flag FIXME_FLAG_08"

        assert len(value.lod_switch_distances) <= 0xFF
        binary_writer.write_u8(len(value.lod_switch_distances), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.lod_switch_distances,
            BinaryWriter.write_float_args,
            None,
            endianness,
        )

        binary_writer.write_u32(value.scene_node_count, endianness)
        binary_writer.write_u32(value.scene_node_capacity, endianness)

        assert len(value.active_scene_node_indices) <= 0xFF
        binary_writer.write_u8(len(value.active_scene_node_indices), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.active_scene_node_indices,
            BinaryWriter.write_u32_args,
            None,
            endianness,
        )

        binary_writer.write_u32(value.c, endianness)
        binary_writer.write_u16(value.d, endianness)
        binary_writer.write(b"\0" * 2)
        binary_writer.write_u16(value.e, endianness)
        binary_writer.write(b"\0" * 2)

        assert len(value.entries10) <= 0xFF
        binary_writer.write_u8(len(value.entries10), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.entries10, ThreeDObjDbPcEntryEntry10.binwrite, None, endianness
        )

        assert len(value.root_scene_nodes) <= 0xFF
        binary_writer.write_u8(len(value.root_scene_nodes), endianness)
        binary_writer.write(b"\0" * 3)
        binary_writer.write_list(
            value.root_scene_nodes,
            ThreeDObjDbPcSceneNode.binwrite,
            (value.flags,),
            endianness,
        )


@dataclass
class ThreeDObjDbPcEntry3(BinRead, BinWrite):
    a: int
    b: int
    c: int

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry3":
        a = binary_reader.read_u16(endianness)
        b = binary_reader.read_u8(endianness)
        c = binary_reader.read_u8(endianness)
        return ThreeDObjDbPcEntry3(a, b, c)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry3",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u16(value.a, endianness)
        binary_writer.write_u8(value.b, endianness)
        binary_writer.write_u8(value.c, endianness)


@dataclass
class ThreeDObjDbPcEntry4(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry4":
        a = binary_reader.read_list(6, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntry4(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry4",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 6
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntry5Entry(BinRead, BinWrite):
    a: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry5Entry":
        a = binary_reader.read_list(6, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntry5Entry(a)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry5Entry",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.a) == 6
        binary_writer.write_list(value.a, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPcEntry5(BinRead, BinWrite):
    entries: list[ThreeDObjDbPcEntry5Entry]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry5":
        num_entries = binary_reader.read_u32(endianness)
        entries = binary_reader.read_list(
            num_entries, ThreeDObjDbPcEntry5Entry.binread, None, endianness
        )
        return ThreeDObjDbPcEntry5(entries)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry5",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(len(value.entries), endianness)
        binary_writer.write_list(
            value.entries, ThreeDObjDbPcEntry5Entry.binwrite, None, endianness
        )


@dataclass
class ThreeDObjDbPcEntry6(BinRead, BinWrite):
    a: int
    b: int
    entries: list[int]
    c: int
    d: list[int]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPcEntry6":
        a = binary_reader.read_u32(endianness)
        b = binary_reader.read_u32(endianness)
        num_entries = binary_reader.read_u32(endianness)
        entries = binary_reader.read_list(
            num_entries, BinaryReader.read_u8_args, None, endianness
        )
        c = binary_reader.read_u32(endianness)
        d = binary_reader.read_list(21, BinaryReader.read_u32_args, None, endianness)
        return ThreeDObjDbPcEntry6(a, b, entries, c, d)

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPcEntry6",
        args: None,
        endianness: Endianness,
    ) -> None:
        assert len(value.d) == 21
        binary_writer.write_u32(value.a, endianness)
        binary_writer.write_u32(value.b, endianness)
        binary_writer.write_u32(len(value.entries), endianness)
        binary_writer.write_list(
            value.entries, BinaryWriter.write_u8_args, None, endianness
        )
        binary_writer.write_u32(value.c, endianness)
        binary_writer.write_list(value.d, BinaryWriter.write_u32_args, None, endianness)


@dataclass
class ThreeDObjDbPc(BinRead, BinWrite):
    file_format_version: int
    entries: list[ThreeDObjDbPcEntry]
    c: int
    d: int
    e: int
    f: int
    g: int
    h: int
    i: int
    j: int
    k: int
    l: int
    m: int
    n: int
    o: int
    q: int
    r: typing.Optional[int]
    s: typing.Optional[int]
    entries2: list[int]
    entries3: list[ThreeDObjDbPcEntry3]
    entries4: list[ThreeDObjDbPcEntry4]
    t: int
    entries5: list[ThreeDObjDbPcEntry5]
    u: int
    entries6: list[ThreeDObjDbPcEntry6]

    @classmethod
    def binread(
        cls, binary_reader: BinaryReader, args: None, endianness: Endianness
    ) -> "ThreeDObjDbPc":
        file_format_version = binary_reader.read_u32(endianness)
        num_entries = binary_reader.read_u32(endianness)
        c = binary_reader.read_u32(endianness)
        d = binary_reader.read_u32(endianness)
        e = binary_reader.read_u32(endianness)
        f = binary_reader.read_u32(endianness)
        g = binary_reader.read_u32(endianness)
        h = binary_reader.read_u32(endianness)
        i = binary_reader.read_u32(endianness)
        j = binary_reader.read_u32(endianness)
        k = binary_reader.read_u32(endianness)
        l = binary_reader.read_u32(endianness)
        m = binary_reader.read_u32(endianness)
        n = binary_reader.read_u32(endianness)
        o = binary_reader.read_u32(endianness)
        num_entries2 = binary_reader.read_u32(endianness)
        q = binary_reader.read_u32(endianness)

        r = None
        s = None
        if file_format_version > 17:
            r = binary_reader.read_u32(endianness)
            s = binary_reader.read_u32(endianness)

        entries = binary_reader.read_list(
            num_entries, ThreeDObjDbPcEntry.binread, None, endianness
        )

        entries2: list[int] = []
        entries3: list[ThreeDObjDbPcEntry3] = []
        entries4: list[ThreeDObjDbPcEntry4] = []
        if num_entries2 != 0:
            num_entries3 = binary_reader.read_u32(endianness)
            num_entries4 = binary_reader.read_u32(endianness)
            entries2 = binary_reader.read_list(
                num_entries2, BinaryReader.read_u32_args, None, endianness
            )
            entries3 = binary_reader.read_list(
                num_entries3, ThreeDObjDbPcEntry3.binread, None, endianness
            )
            entries4 = binary_reader.read_list(
                num_entries4, ThreeDObjDbPcEntry4.binread, None, endianness
            )

        num_entries5 = binary_reader.read_u32(endianness)
        t = binary_reader.read_u32(endianness)
        entries5 = binary_reader.read_list(
            num_entries5, ThreeDObjDbPcEntry5.binread, None, endianness
        )

        num_entries6 = binary_reader.read_u32(endianness)
        u = binary_reader.read_u32(endianness)
        entries6 = binary_reader.read_list(
            num_entries6, ThreeDObjDbPcEntry6.binread, None, endianness
        )

        return ThreeDObjDbPc(
            file_format_version,
            entries,
            c,
            d,
            e,
            f,
            g,
            h,
            i,
            j,
            k,
            l,
            m,
            n,
            o,
            q,
            r,
            s,
            entries2,
            entries3,
            entries4,
            t,
            entries5,
            u,
            entries6,
        )

    @classmethod
    def binwrite(
        cls,
        binary_writer: BinaryWriter,
        value: "ThreeDObjDbPc",
        args: None,
        endianness: Endianness,
    ) -> None:
        binary_writer.write_u32(value.file_format_version, endianness)
        binary_writer.write_u32(len(value.entries), endianness)
        binary_writer.write_u32(value.c, endianness)
        binary_writer.write_u32(value.d, endianness)
        binary_writer.write_u32(value.e, endianness)
        binary_writer.write_u32(value.f, endianness)
        binary_writer.write_u32(value.g, endianness)
        binary_writer.write_u32(value.h, endianness)
        binary_writer.write_u32(value.i, endianness)
        binary_writer.write_u32(value.j, endianness)
        binary_writer.write_u32(value.k, endianness)
        binary_writer.write_u32(value.l, endianness)
        binary_writer.write_u32(value.m, endianness)
        binary_writer.write_u32(value.n, endianness)
        binary_writer.write_u32(value.o, endianness)
        binary_writer.write_u32(len(value.entries2), endianness)
        binary_writer.write_u32(value.q, endianness)

        if value.file_format_version > 17:
            assert value.r is not None
            assert value.s is not None
            binary_writer.write_u32(value.r, endianness)
            binary_writer.write_u32(value.s, endianness)
        else:
            assert value.r is None
            assert value.s is None

        binary_writer.write_list(
            value.entries, ThreeDObjDbPcEntry.binwrite, None, endianness
        )

        if len(value.entries2) != 0:
            binary_writer.write_u32(len(value.entries3), endianness)
            binary_writer.write_u32(len(value.entries4), endianness)
            binary_writer.write_list(
                value.entries2, BinaryWriter.write_u32_args, None, endianness
            )
            binary_writer.write_list(
                value.entries3, ThreeDObjDbPcEntry3.binwrite, None, endianness
            )
            binary_writer.write_list(
                value.entries4, ThreeDObjDbPcEntry4.binwrite, None, endianness
            )
        else:
            assert len(value.entries3) == 0
            assert len(value.entries4) == 0

        binary_writer.write_u32(len(value.entries5), endianness)
        binary_writer.write_u32(value.t, endianness)
        binary_writer.write_list(
            value.entries5, ThreeDObjDbPcEntry5.binwrite, None, endianness
        )

        binary_writer.write_u32(len(value.entries6), endianness)
        binary_writer.write_u32(value.u, endianness)
        binary_writer.write_list(
            value.entries6, ThreeDObjDbPcEntry6.binwrite, None, endianness
        )


@dataclass
class ThreeDObjPc:
    three_d_obj_db_pc: ThreeDObjDbPc
    three_d_objs_pc: ThreeDObjsPc
    three_d_objsp_pc: ThreeDObjspPc
    bininfo_bin: BininfoBin
    textures_pc: TexturesPc

    @classmethod
    def from_directory_path(cls, path: Path, endianness: Endianness) -> "ThreeDObjPc":
        three_d_obj_db_pc_path = path / "3dobjdb.pc"
        three_d_objs_pc_path = path / "3dobjs.pc"
        three_d_objsp_pc_path = path / "3dobjsp.pc"
        bininfo_bin_path = path / "bininfo.bin"
        textures_pc_path = path / "textures.pc"

        three_d_obj_db_pc = ThreeDObjDbPc.binread_from_path(
            three_d_obj_db_pc_path, None, endianness
        )
        three_d_objs_pc = ThreeDObjsPc.binread_from_path_decompress(
            three_d_objs_pc_path,
            None,
            endianness,
        )
        three_d_objsp_pc = ThreeDObjspPc.binread_from_path_decompress(
            three_d_objsp_pc_path, (three_d_objs_pc,), endianness
        )
        bininfo_bin = BininfoBin.binread_from_path(bininfo_bin_path, None, endianness)
        textures_pc = TexturesPc.binread_from_path_decompress(
            textures_pc_path, None, endianness
        )

        return ThreeDObjPc(
            three_d_obj_db_pc,
            three_d_objs_pc,
            three_d_objsp_pc,
            bininfo_bin,
            textures_pc,
        )

    def to_directory_path(self, path: Path, endianness: Endianness) -> None:
        path.mkdir(parents=True, exist_ok=True)

        three_d_obj_db_pc_path = path / "3dobjdb.pc"
        three_d_objs_pc_path = path / "3dobjs.pc"
        three_d_objsp_pc_path = path / "3dobjsp.pc"
        bininfo_bin_path = path / "bininfo.bin"
        textures_pc_path = path / "textures.pc"

        ThreeDObjDbPc.binwrite_to_path(
            three_d_obj_db_pc_path, self.three_d_obj_db_pc, None, endianness
        )
        ThreeDObjsPc.binwrite_to_path_compress(
            three_d_objs_pc_path, self.three_d_objs_pc, None, endianness
        )
        ThreeDObjspPc.binwrite_to_path_compress(
            three_d_objsp_pc_path,
            self.three_d_objsp_pc,
            (self.three_d_objs_pc,),
            endianness,
        )
        BininfoBin.binwrite_to_path(
            bininfo_bin_path, self.bininfo_bin, None, endianness
        )
        TexturesPc.binwrite_to_path_compress(
            textures_pc_path, self.textures_pc, None, endianness
        )
