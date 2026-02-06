from pathlib import Path
from uuid import uuid4

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .modules.libfror.binrw import Endianness
from .modules.libfror.types import TexturesPc, ThreeDObjPc, VertexColors, VertexNormals


def _load_packed_images(textures_pc: TexturesPc):
    temp_dir = Path(bpy.app.tempdir or ".")
    temp_dir.mkdir(parents=True, exist_ok=True)

    packed_images = []
    for textures_pc_entry4 in textures_pc.entries4:
        dds = textures_pc_entry4.to_dds()
        path = temp_dir / f"fror_{uuid4().hex}.dds"
        path.write_bytes(dds)
        try:
            image = bpy.data.images.load(str(path))
            image.use_fake_user = True
            image.pack()
        finally:
            path.unlink()
        packed_images.append(image)
    return packed_images


class ImportFROR(Operator, ImportHelper):
    bl_idname = "fror_blender.import_fror"
    bl_label = "Import Ford Racing Off Road"
    bl_description = "Load a Ford Racing Off Road 3dobj"

    def execute(self, context: bpy.types.Context) -> set[str]:
        directory_path = Path(self.filepath)
        endianness = Endianness.LITTLE
        three_d_obj_pc = ThreeDObjPc.from_directory_path(directory_path, endianness)
        three_d_objs_pc = three_d_obj_pc.three_d_objs_pc
        three_d_objsp_pc = three_d_obj_pc.three_d_objsp_pc
        textures_pc = three_d_obj_pc.textures_pc

        packed_images = _load_packed_images(textures_pc)

        for i in range(len(three_d_objsp_pc.vertex_buffers)):
            mesh = bpy.data.meshes.new(f"myBeautifulMesh{i}")
            obj = bpy.data.objects.new(mesh.name, mesh)
            col = bpy.data.collections["Collection"]
            col.objects.link(obj)
            bpy.context.view_layer.objects.active = obj

            vertex_buffer = three_d_objsp_pc.vertex_buffers[i]
            triangle_strip_buffer = three_d_objs_pc.triangle_strip_buffers[i]
            mesh_descriptor = three_d_objs_pc.mesh_descriptors[i]

            vertices = vertex_buffer.positions_z_up()
            edges: list[tuple[int, int]] = []
            faces = triangle_strip_buffer.to_triangles_ccw()

            mesh.from_pydata(vertices, edges, faces)

            mesh.validate(clean_customdata=False)
            mesh.update()

            uvs = vertex_buffer.uvs_v_up()
            if uvs is not None:
                uv_layer = mesh.uv_layers.new()
                for polygon in mesh.polygons:
                    for loop_index in polygon.loop_indices:
                        vertex_index = mesh.loops[loop_index].vertex_index
                        uv_layer.data[loop_index].uv = uvs[vertex_index]

            if mesh_descriptor.w != -1:
                image = packed_images[mesh_descriptor.w]

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

            match vertex_buffer.normals_or_colors_z_up():
                case VertexNormals(normals):
                    assert len(normals) == len(vertices)
                    for polygon in mesh.polygons:
                        polygon.use_smooth = True
                    mesh.normals_split_custom_set(
                        [normals[loop.vertex_index] for loop in mesh.loops]
                    )
                case VertexColors(colors):
                    color_layer = mesh.color_attributes.new(
                        name="Color", type="FLOAT_COLOR", domain="CORNER"
                    )
                    for polygon in mesh.polygons:
                        for loop_index in polygon.loop_indices:
                            vertex_index = mesh.loops[loop_index].vertex_index
                            color_layer.data[loop_index].color = colors[vertex_index]

            if uvs is not None:
                mesh.calc_tangents()
            mesh.validate(clean_customdata=False)
            mesh.update()

        return {"FINISHED"}


def menu_func_import_fror(self, context: bpy.types.Context) -> None:
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register() -> None:
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)
