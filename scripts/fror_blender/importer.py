from pathlib import Path

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from libfror.binrw import Endianness
from libfror.compression import get_decompressed_binary_reader
from libfror.types import ThreeDObjsPc, VertexBuffer, Mesh


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


def fror_to_blender(position: tuple[float, float, float]) -> tuple[float, float, float]:
    return (position[0], position[2], position[1])


def fror_to_blender_uvs2(position: tuple[float, float]) -> tuple[float, float]:
    return (position[0], 1 - position[1])


class ImportFROR(Operator, ImportHelper):  # type: ignore
    bl_idname = "fror_blender.import_fror"
    bl_label = "Import Ford Racing Off Road"
    bl_description = "Load a Ford Racing Off Road 3dobj"

    def execute(self, context: bpy.types.Context) -> set[str]:
        directory_path = Path(self.filepath)  # type: ignore
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
                decompressed_data_binary_reader, None, endianness
            )
            assert len(decompressed_data_binary_reader.read()) == 0

        with open(three_d_objsp_pc_path, "rb") as three_d_objsp_pc_file:
            decompressed_data_binary_reader = get_decompressed_binary_reader(
                three_d_objsp_pc_file
            )
            vertex_buffers = []
            for mesh_descriptor in three_d_objs_pc.mesh_descriptors:
                vertex_buffers.append(
                    VertexBuffer.binread(
                        decompressed_data_binary_reader,
                        (mesh_descriptor.num_vertices, mesh_descriptor.w),
                        endianness,
                    )
                )
            assert len(decompressed_data_binary_reader.read()) == 0

        for i in range(len(vertex_buffers)):
            mesh = bpy.data.meshes.new(f"myBeautifulMesh{i}")  # type: ignore
            obj = bpy.data.objects.new(mesh.name, mesh)  # type: ignore
            col = bpy.data.collections["Collection"]  # type: ignore
            col.objects.link(obj)  # type: ignore
            bpy.context.view_layer.objects.active = obj  # type: ignore

            first_mesh = Mesh(
                vertex_buffers[i], three_d_objs_pc.triangle_strip_buffers[i]
            )
            verts = first_mesh.vertex_buffer.positions
            uvs = first_mesh.vertex_buffer.uvs
            uvs2 = first_mesh.vertex_buffer.uvs2

            blender_verts = list(map(fror_to_blender, verts))

            edges: list[tuple[int, int]] = []
            faces = []
            for ngon in first_mesh.triangle_strip_buffer.triangle_strips:
                indexed_triangles = triangle_strip_to_indexed_triangles(ngon.indices)
                faces.extend(indexed_triangles)

            mesh.from_pydata(blender_verts, edges, faces)

            if uvs2 is not None:
                blender_uvs2 = list(map(fror_to_blender_uvs2, uvs2))
                uv_layer = mesh.uv_layers.new()
                for polygon in mesh.polygons:
                    for loop_index in polygon.loop_indices:
                        vertex_index = mesh.loops[loop_index].vertex_index
                        uv_layer.data[loop_index].uv = blender_uvs2[vertex_index]

        return {"FINISHED"}


def menu_func_import_fror(self, context: bpy.types.Context) -> None:
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register() -> None:
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)  # type: ignore


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)  # type: ignore
