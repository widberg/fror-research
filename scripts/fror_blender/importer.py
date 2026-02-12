from pathlib import Path
from uuid import uuid4

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .modules.libfror.binrw import Endianness
from .modules.libfror.types import TexturesPc, ThreeDObjPc, VertexColors, VertexNormals

NO_TEXTURE_INDEX = -1
COLOR_ATTRIBUTE_NAME = "Color"
MESH_NAME_PREFIX = "fror_mesh_"
MATERIAL_NAME_PREFIX = "fror_material_"
VERTEX_COLOR_MATERIAL_NAME_PREFIX = "fror_vertex_color_"
SOURCE_DIRECTORY_PROP = "fror_source_directory"
MESH_INDEX_PROP = "fror_mesh_index"


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


def _create_material_from_image(
    image: bpy.types.Image, name: str
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
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

    return material


def _create_material_from_vertex_color(
    name: str, color_attribute_name: str = COLOR_ATTRIBUTE_NAME
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    nodes.clear()

    attr_node = nodes.new("ShaderNodeAttribute")
    attr_node.attribute_name = color_attribute_name
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    out_node = nodes.new("ShaderNodeOutputMaterial")

    links.new(attr_node.outputs["Color"], bsdf_node.inputs["Base Color"])
    links.new(attr_node.outputs["Alpha"], bsdf_node.inputs["Alpha"])
    links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

    return material


def _apply_vertex_color_global_illumination(
    material: bpy.types.Material, color_attribute_name: str = COLOR_ATTRIBUTE_NAME
) -> None:
    if not material.use_nodes or material.node_tree is None:
        return

    nodes = material.node_tree.nodes
    links = material.node_tree.links

    image_node = next(
        (node for node in nodes if node.bl_idname == "ShaderNodeTexImage"), None
    )
    bsdf_node = next(
        (node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
        None,
    )
    if image_node is None or bsdf_node is None:
        return

    attr_node = nodes.new("ShaderNodeAttribute")
    attr_node.attribute_name = color_attribute_name

    multiply_node = nodes.new("ShaderNodeMixRGB")
    multiply_node.blend_type = "MULTIPLY"
    multiply_node.inputs["Fac"].default_value = 1.0

    mix_node = nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = "MIX"

    for link in list(bsdf_node.inputs["Base Color"].links):
        links.remove(link)

    links.new(image_node.outputs["Color"], multiply_node.inputs["Color1"])
    links.new(attr_node.outputs["Color"], multiply_node.inputs["Color2"])
    links.new(attr_node.outputs["Alpha"], mix_node.inputs["Fac"])
    links.new(image_node.outputs["Color"], mix_node.inputs["Color1"])
    links.new(multiply_node.outputs["Color"], mix_node.inputs["Color2"])
    links.new(mix_node.outputs["Color"], bsdf_node.inputs["Base Color"])


def _load_packed_materials(textures_pc: TexturesPc) -> list[bpy.types.Material]:
    packed_images = _load_packed_images(textures_pc)
    return [
        _create_material_from_image(image, f"{MATERIAL_NAME_PREFIX}{i}")
        for i, image in enumerate(packed_images)
    ]


def _load_packed_gi_materials(
    packed_materials: list[bpy.types.Material],
    color_attribute_name: str = COLOR_ATTRIBUTE_NAME,
) -> list[bpy.types.Material]:
    gi_materials: list[bpy.types.Material] = []
    for material in packed_materials:
        gi_material = material.copy()
        gi_material.name = f"{material.name}_gi"
        _apply_vertex_color_global_illumination(gi_material, color_attribute_name)
        gi_materials.append(gi_material)
    return gi_materials


def import_fror_scene(
    context: bpy.types.Context,
    directory_path: Path,
    endianness: Endianness = Endianness.LITTLE,
) -> None:
    context.scene[SOURCE_DIRECTORY_PROP] = str(directory_path)
    three_d_obj_pc = ThreeDObjPc.from_directory_path(directory_path, endianness)
    three_d_objs_pc = three_d_obj_pc.three_d_objs_pc
    three_d_objsp_pc = three_d_obj_pc.three_d_objsp_pc
    textures_pc = three_d_obj_pc.textures_pc

    packed_materials = _load_packed_materials(textures_pc)
    packed_gi_materials = _load_packed_gi_materials(packed_materials)
    target_collection = context.collection or context.scene.collection

    for i, (
        vertex_buffer,
        triangle_strip_buffer,
        mesh_descriptor,
    ) in enumerate(
        zip(
            three_d_objsp_pc.vertex_buffers,
            three_d_objs_pc.triangle_strip_buffers,
            three_d_objs_pc.mesh_descriptors,
            strict=True,
        ),
    ):
        vertex_buffer_z_up_v_up = vertex_buffer.to_z_up_v_up()
        mesh = bpy.data.meshes.new(f"{MESH_NAME_PREFIX}{i}")
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj[MESH_INDEX_PROP] = i
        target_collection.objects.link(obj)

        vertices = vertex_buffer_z_up_v_up.positions
        edges: list[tuple[int, int]] = []
        faces = triangle_strip_buffer.to_triangles_ccw()

        mesh.from_pydata(vertices, edges, faces)
        mesh.validate(clean_customdata=False)
        mesh.update()

        loop_vertex_indices = [loop.vertex_index for loop in mesh.loops]
        uvs = vertex_buffer_z_up_v_up.uvs
        if uvs is not None:
            uv_layer = mesh.uv_layers.new()
            for loop_index, vertex_index in enumerate(loop_vertex_indices):
                uv_layer.data[loop_index].uv = uvs[vertex_index]

        texture_index = mesh_descriptor.texture_index
        if texture_index != NO_TEXTURE_INDEX:
            assert 0 <= texture_index < len(packed_materials)
            mesh.materials.append(packed_materials[texture_index])

        match vertex_buffer_z_up_v_up.normals_or_colors:
            case VertexNormals(normals=normals):
                assert len(normals) == len(vertices)
                for polygon in mesh.polygons:
                    polygon.use_smooth = True
                mesh.normals_split_custom_set(
                    [normals[vertex_index] for vertex_index in loop_vertex_indices]
                )
            case VertexColors(colors=colors):
                color_layer = mesh.color_attributes.new(
                    name=COLOR_ATTRIBUTE_NAME, type="FLOAT_COLOR", domain="CORNER"
                )
                for loop_index, vertex_index in enumerate(loop_vertex_indices):
                    color_layer.data[loop_index].color = colors[vertex_index]
                if texture_index != NO_TEXTURE_INDEX:
                    mesh.materials[0] = packed_gi_materials[texture_index]
                else:
                    mesh.materials.append(
                        _create_material_from_vertex_color(
                            f"{VERTEX_COLOR_MATERIAL_NAME_PREFIX}{i}",
                            COLOR_ATTRIBUTE_NAME,
                        )
                    )

        if uvs is not None:
            mesh.calc_tangents()
        mesh.validate(clean_customdata=False)
        mesh.update()


class ImportFROR(Operator, ImportHelper):
    bl_idname = "fror_blender.import_fror"
    bl_label = "Import Ford Racing Off Road"
    bl_description = "Load a Ford Racing Off Road 3dobj"

    def execute(self, context: bpy.types.Context) -> set[str]:
        import_fror_scene(context, Path(self.filepath), Endianness.LITTLE)
        return {"FINISHED"}


def menu_func_import_fror(self, context: bpy.types.Context) -> None:
    self.layout.operator(ImportFROR.bl_idname, text="Ford Racing Off Road")


def register() -> None:
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_fror)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_fror)
