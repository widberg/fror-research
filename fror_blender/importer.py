from pathlib import Path

import bpy
import bmesh
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from .binread import Endianness
from .decompress import get_decompressed_binary_reader
from .types import ThreeDObjsPc, VertexBuffer, Mesh


def triangle_strip_to_indexed_triangles(strip_indices):
    indexed_triangles = []
    for i in range(2, len(strip_indices)):
        if i % 2 == 0:
            # Even triangle: (v0, v1, v2)
            indexed_triangles.append(
                [strip_indices[i - 2], strip_indices[i - 1], strip_indices[i]]
            )
        else:
            # Odd triangle: (v1, v0, v2)
            indexed_triangles.append(
                [strip_indices[i - 1], strip_indices[i - 2], strip_indices[i]]
            )
    return indexed_triangles


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

        endianness = Endianness.LITTLE

        with open(three_d_objs_pc_path, "rb") as three_d_objs_pc_file:
            decompressed_data_binary_reader = get_decompressed_binary_reader(
                three_d_objs_pc_file
            )
            three_d_objs_pc = ThreeDObjsPc.binread(
                decompressed_data_binary_reader, endianness
            )
            assert len(decompressed_data_binary_reader.read()) == 0

        with open(three_d_objsp_pc_path, "rb") as three_d_objsp_pc_file:
            decompressed_data_binary_reader = get_decompressed_binary_reader(
                three_d_objsp_pc_file
            )
            vertex_buffers = []
            for mesh_descriptor in three_d_objs_pc.mesh_descriptors:
                # print(f"VertexBuffer<{mesh_descriptor.num_vertices}, {int(mesh_descriptor.w >= 0)}> vertex_buffer_{decompressed_data_binary_reader.tell():X};")
                vertex_buffers.append(
                    VertexBuffer.binread(
                        decompressed_data_binary_reader,
                        mesh_descriptor.num_vertices,
                        mesh_descriptor.w,
                        endianness,
                    )
                )
            assert len(decompressed_data_binary_reader.read()) == 0

        for i in range(len(vertex_buffers)):
            first_mesh = Mesh(vertex_buffers[i], three_d_objs_pc.ngon_buffers[i])

            verts = first_mesh.vertex_buffer.positions
            mesh = bpy.data.meshes.new("myBeautifulMesh" + str(i))
            obj = bpy.data.objects.new(mesh.name, mesh)
            col = bpy.data.collections["Collection"]
            col.objects.link(obj)
            bpy.context.view_layer.objects.active = obj

            verts = first_mesh.vertex_buffer.positions
            edges = []
            faces = []
            for ngon in first_mesh.ngon_buffer.ngons:
                indexed_triangles = triangle_strip_to_indexed_triangles(ngon.indices)
                faces.extend(indexed_triangles)

            mesh.from_pydata(verts, edges, faces)

        return {"FINISHED"}


def menu_func_import_fror(self, context):
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)
