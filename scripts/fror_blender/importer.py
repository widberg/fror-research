import tempfile
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .modules.libfror.binrw import Endianness
from .modules.libfror.types import ThreeDObjPc


class ImportFROR(Operator, ImportHelper):  # type: ignore
    bl_idname = "fror_blender.import_fror"
    bl_label = "Import Ford Racing Off Road"
    bl_description = "Load a Ford Racing Off Road 3dobj"

    def execute(self, context: bpy.types.Context) -> set[str]:
        directory_path = Path(self.filepath)  # type: ignore
        endianness = Endianness.LITTLE
        three_d_obj = ThreeDObjPc.from_directory_path(directory_path, endianness)

        for i in range(len(three_d_obj.three_d_objsp_pc.vertex_buffers)):
            mesh = bpy.data.meshes.new(f"myBeautifulMesh{i}")  # type: ignore
            obj = bpy.data.objects.new(mesh.name, mesh)  # type: ignore
            col = bpy.data.collections["Collection"]  # type: ignore
            col.objects.link(obj)  # type: ignore
            bpy.context.view_layer.objects.active = obj  # type: ignore

            vertex_buffer = three_d_obj.three_d_objsp_pc.vertex_buffers[i]
            triangle_strip_buffer = three_d_obj.three_d_objs_pc.triangle_strip_buffers[
                i
            ]
            mesh_descriptor = three_d_obj.three_d_objs_pc.mesh_descriptors[i]

            vertices = vertex_buffer.positions_z_up()
            edges: list[tuple[int, int]] = []
            faces = triangle_strip_buffer.to_triangles()

            mesh.from_pydata(vertices, edges, faces)

            uvs2 = vertex_buffer.uvs2_v_up()
            if uvs2 is not None:
                uv_layer = mesh.uv_layers.new()
                for polygon in mesh.polygons:
                    for loop_index in polygon.loop_indices:
                        vertex_index = mesh.loops[loop_index].vertex_index
                        uv_layer.data[loop_index].uv = uvs2[vertex_index]

            if mesh_descriptor.w != -1:
                textures_pc_entry4 = three_d_obj.textures_pc.entries4[mesh_descriptor.w]
                dds = textures_pc_entry4.to_dds()
                with tempfile.NamedTemporaryFile(
                    "wb", suffix=".dds", delete=False
                ) as f:
                    f.write(dds)
                    path = Path(f.name)
                image = bpy.data.images.load(str(path))
                image.use_fake_user = True
                image.pack()
                path.unlink()

                material = bpy.data.materials.new("test" + str(i))
                material.use_nodes = True

                nodes = material.node_tree.nodes
                links = material.node_tree.links

                nodes.clear()

                image_node = nodes.new("ShaderNodeTexImage")
                image_node.image = image
                image_node.extension = "REPEAT"

                bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")

                out_node = nodes.new("ShaderNodeOutputMaterial")

                links.new(image_node.outputs["Color"], bsdf_node.inputs["Base Color"])
                links.new(image_node.outputs["Alpha"], bsdf_node.inputs["Alpha"])
                links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

                mesh.materials.append(material)

        return {"FINISHED"}


def menu_func_import_fror(self, context: bpy.types.Context) -> None:
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register() -> None:
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)  # type: ignore


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)  # type: ignore
