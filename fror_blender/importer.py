from pathlib import Path
from io import BytesIO
from dataclasses import dataclass

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from .binread import BinaryReader
from .decompress import decompress


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

    def read_ThreeDObjsPcEntry(binary_reader: BinaryReader, endianness=None):
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


class ImportFROR(Operator, ImportHelper):
    bl_idname = "fror_blender.import_fror"
    bl_label = "Import Ford Racing Off Road"
    bl_description = "Load a Ford Racing Off Road 3dobj"

    def execute(self, context):
        directory_path = Path(self.filepath)
        three_d_obj_db_pc_path = directory_path / "3dobjdb.pc"
        three_d_objs_pc_path = directory_path / "3dobjs.pc"  # compressed
        three_d_objsp_pc_path = directory_path / "3dobjsp.pc"  # compressed
        bininfo_bin = directory_path / "bininfo.bin"
        textures_pc = directory_path / "textures.pc"  # compressed
        succeeded = True
        files = [
            three_d_obj_db_pc_path,
            three_d_objs_pc_path,
            three_d_objsp_pc_path,
            bininfo_bin,
            textures_pc,
        ]
        for file in files:
            if not file.exists():
                succeeded = False
                self.report({"ERROR"}, f'"{file}" does not exist.')
        if not succeeded:
            return {"CANCELED"}

        with open(three_d_objs_pc_path, "rb") as three_d_objs_pc_file:
            three_d_objs_pc_binary_reader = BinaryReader(three_d_objs_pc_file)
            decompressed_data = decompress(three_d_objs_pc_binary_reader)
            decompressed_data_binary_reader = BinaryReader(BytesIO(decompressed_data))
            num_entries = decompressed_data_binary_reader.read_u32()
            print(num_entries)
            decompressed_data_binary_reader.skip(0xC)
            entries = decompressed_data_binary_reader.read_list(
                num_entries,
                ThreeDObjsPcEntry.read_ThreeDObjsPcEntry
            )
            print(entries)

        return {"FINISHED"}


def menu_func_import_fror(self, context):
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)
