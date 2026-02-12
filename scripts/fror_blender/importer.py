import struct
from pathlib import Path
from uuid import uuid4

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .modules.libfror.binrw import Endianness
from .modules.libfror.types import (
    THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY,
    BininfoBin,
    TexturesPc,
    ThreeDObjDbPc,
    ThreeDObjDbPcSceneNode,
    ThreeDObjPc,
    ThreeDObjsPc,
    VertexColors,
    VertexNormals,
    y_up_to_z_up,
)

NO_TEXTURE_INDEX = -1
COLOR_ATTRIBUTE_NAME = "Color"
MESH_NAME_PREFIX = "fror_mesh_"
SCENE_NODE_NAME_PREFIX = "fror_scene_node_"
MATERIAL_NAME_PREFIX = "fror_material_"
VERTEX_COLOR_MATERIAL_NAME_PREFIX = "fror_vertex_color_"
SOURCE_DIRECTORY_PROP = "fror_source_directory"
MESH_INDEX_PROP = "fror_mesh_index"
SCENE_NODE_INDEX_PROP = "fror_scene_node_index"


def _u32_to_float(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]


def _safe_indexed_name(names: list[str], index: int) -> str | None:
    if 0 <= index < len(names):
        return names[index]
    return None


def _name_suffix(name: str) -> str:
    sanitized = name.strip()
    for char in "\\/:*?\"<>|\r\n\t":
        sanitized = sanitized.replace(char, "_")
    return sanitized


def _scene_node_translation_z_up(
    scene_node: ThreeDObjDbPcSceneNode,
) -> tuple[float, float, float]:
    translation_y_up = (
        _u32_to_float(scene_node.b),
        _u32_to_float(scene_node.c),
        _u32_to_float(scene_node.d),
    )
    return y_up_to_z_up(translation_y_up)


def _mesh_indices_to_scene_node_indices(
    three_d_objs_pc: ThreeDObjsPc,
) -> list[int | None]:
    num_mesh_descriptors = len(three_d_objs_pc.mesh_descriptors)
    mesh_indices_to_scene_node_indices: list[int | None] = [None] * num_mesh_descriptors

    for scene_node_index, entry in enumerate(three_d_objs_pc.entries):
        for lod in (entry.lod_near, entry.lod_far):
            begin = lod.begin
            end = begin + lod.length
            assert 0 <= begin <= end <= num_mesh_descriptors
            for mesh_index in range(begin, end):
                existing_scene_node_index = mesh_indices_to_scene_node_indices[mesh_index]
                if existing_scene_node_index is None:
                    mesh_indices_to_scene_node_indices[mesh_index] = scene_node_index
                else:
                    assert existing_scene_node_index == scene_node_index

    return mesh_indices_to_scene_node_indices


def _collect_scene_node_hierarchy(
    three_d_obj_db_pc: ThreeDObjDbPc,
) -> tuple[dict[int, tuple[float, float, float]], dict[int, int]]:
    scene_node_locations: dict[int, tuple[float, float, float]] = {}
    scene_node_parents: dict[int, int] = {}

    def visit_scene_node(
        scene_node: ThreeDObjDbPcSceneNode,
        flags: int,
        parent_scene_node_index: int | None,
    ) -> None:
        scene_node_index = scene_node.scene_node_index

        if parent_scene_node_index is not None:
            scene_node_parents.setdefault(scene_node_index, parent_scene_node_index)

        if (flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) != 0:
            return

        scene_node_locations.setdefault(
            scene_node_index,
            _scene_node_translation_z_up(scene_node),
        )

        for child_node in scene_node.child_nodes:
            visit_scene_node(child_node, flags, scene_node_index)

    for entry in three_d_obj_db_pc.entries:
        for root_scene_node in entry.root_scene_nodes:
            visit_scene_node(root_scene_node, entry.flags, None)

    return scene_node_locations, scene_node_parents


def _build_scene_node_index_aliases(
    three_d_obj_db_pc: ThreeDObjDbPc,
    num_scene_nodes: int,
) -> dict[int, int]:
    scene_node_index_aliases: dict[int, int] = {}
    num_entries = len(three_d_obj_db_pc.entries)
    for entry_index in range(min(num_entries, num_scene_nodes)):
        entry = three_d_obj_db_pc.entries[entry_index]
        if (entry.flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) == 0:
            continue
        if len(entry.root_scene_nodes) == 0:
            continue
        aliased_scene_node_index = entry.root_scene_nodes[0].scene_node_index
        if aliased_scene_node_index < 0 or aliased_scene_node_index >= num_scene_nodes:
            continue
        if aliased_scene_node_index == entry_index:
            continue
        scene_node_index_aliases[entry_index] = aliased_scene_node_index
    return scene_node_index_aliases


def _collect_scene_node_transforms_from_entries5(
    three_d_obj_db_pc: ThreeDObjDbPc,
    num_scene_nodes: int,
) -> tuple[dict[int, tuple[float, float, float]], dict[int, float]]:
    scene_node_transform_candidates: dict[
        int, list[tuple[tuple[float, float, float], float, int]]
    ] = {}
    scene_node_index_aliases = _build_scene_node_index_aliases(
        three_d_obj_db_pc,
        num_scene_nodes,
    )

    for entry in three_d_obj_db_pc.entries:
        for entry5 in entry.entries5:
            scene_node_index = entry5.a
            if scene_node_index < 0 or scene_node_index >= num_scene_nodes:
                continue
            scene_node_index = scene_node_index_aliases.get(
                scene_node_index,
                scene_node_index,
            )
            location = y_up_to_z_up(
                (
                    entry5.d,
                    _u32_to_float(entry5.e),
                    _u32_to_float(entry5.f),
                )
            )
            yaw = _u32_to_float(entry5.g)
            scene_node_transform = (location, yaw, entry5.b)
            candidates = scene_node_transform_candidates.setdefault(scene_node_index, [])
            if scene_node_transform not in candidates:
                candidates.append(scene_node_transform)

    scene_node_locations: dict[int, tuple[float, float, float]] = {}
    scene_node_yaws: dict[int, float] = {}
    for scene_node_index, candidates in scene_node_transform_candidates.items():
        preferred_candidates = [
            (location, yaw) for location, yaw, b in candidates if b != 0xFFFF
        ]
        if len(preferred_candidates) == 1:
            scene_node_location, scene_node_yaw = preferred_candidates[0]
            scene_node_locations[scene_node_index] = scene_node_location
            scene_node_yaws[scene_node_index] = scene_node_yaw
            continue
        if len(candidates) == 1:
            scene_node_location, scene_node_yaw, _ = candidates[0]
            scene_node_locations[scene_node_index] = scene_node_location
            scene_node_yaws[scene_node_index] = scene_node_yaw

    return scene_node_locations, scene_node_yaws


def _collect_scene_node_labels(
    three_d_obj_db_pc: ThreeDObjDbPc,
    bininfo_bin: BininfoBin,
    num_scene_nodes: int,
) -> dict[int, str]:
    scene_node_sub_object_names: dict[int, list[str]] = {}
    scene_node_shape_names: dict[int, list[str]] = {}
    scene_node_root_shape_names: dict[int, list[str]] = {}

    def append_sub_object_name(scene_node_index: int, sub_object_name: str) -> None:
        if scene_node_index < 0 or scene_node_index >= num_scene_nodes:
            return
        scene_node_names = scene_node_sub_object_names.setdefault(scene_node_index, [])
        if sub_object_name not in scene_node_names:
            scene_node_names.append(sub_object_name)

    def append_shape_name(
        scene_node_index: int,
        shape_name: str,
        root_only: bool,
    ) -> None:
        if scene_node_index < 0 or scene_node_index >= num_scene_nodes:
            return
        scene_node_names = scene_node_shape_names.setdefault(scene_node_index, [])
        if shape_name not in scene_node_names:
            scene_node_names.append(shape_name)
        if root_only:
            root_scene_node_names = scene_node_root_shape_names.setdefault(
                scene_node_index, []
            )
            if shape_name not in root_scene_node_names:
                root_scene_node_names.append(shape_name)

    def visit_scene_node(
        scene_node: ThreeDObjDbPcSceneNode,
        flags: int,
        object_shape_name: str | None,
        is_root_node: bool,
    ) -> None:
        scene_node_index = scene_node.scene_node_index
        if object_shape_name is not None:
            append_shape_name(scene_node_index, object_shape_name, is_root_node)

        if (flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) != 0:
            return

        for sub_object_binding in scene_node.sub_object_bindings:
            sub_object_name = _safe_indexed_name(
                bininfo_bin.sub_object_names,
                sub_object_binding.sub_object_name_index,
            )
            if sub_object_name is not None:
                target_scene_node_index = sub_object_binding.scene_node_index
                if 0 <= sub_object_binding.scene_node_index < len(scene_node.child_nodes):
                    target_scene_node_index = scene_node.child_nodes[
                        sub_object_binding.scene_node_index
                    ].scene_node_index
                append_sub_object_name(
                    target_scene_node_index,
                    sub_object_name,
                )

        for child_node in scene_node.child_nodes:
            visit_scene_node(child_node, flags, object_shape_name, False)

    for entry in three_d_obj_db_pc.entries:
        object_shape_name = _safe_indexed_name(
            bininfo_bin.object_shape_names,
            entry.object_shape_name_index,
        )
        for root_scene_node in entry.root_scene_nodes:
            visit_scene_node(root_scene_node, entry.flags, object_shape_name, True)

    scene_node_labels: dict[int, str] = {}
    for scene_node_index in range(num_scene_nodes):
        root_shape_names = scene_node_root_shape_names.get(scene_node_index)
        if root_shape_names is not None and len(root_shape_names) == 1:
            scene_node_labels[scene_node_index] = root_shape_names[0]
            continue

        sub_object_names = scene_node_sub_object_names.get(scene_node_index)
        if sub_object_names is not None and len(sub_object_names) == 1:
            scene_node_labels[scene_node_index] = sub_object_names[0]
            continue

        shape_names = scene_node_shape_names.get(scene_node_index)
        if shape_names is not None and len(shape_names) == 1:
            scene_node_labels[scene_node_index] = shape_names[0]

    return scene_node_labels


def _create_scene_node_objects(
    target_collection: bpy.types.Collection,
    num_scene_nodes: int,
    scene_node_locations: dict[int, tuple[float, float, float]],
    scene_node_yaws: dict[int, float],
    scene_node_parents: dict[int, int],
    scene_node_labels: dict[int, str],
) -> list[bpy.types.Object]:
    scene_node_objects: list[bpy.types.Object] = []

    for scene_node_index in range(num_scene_nodes):
        scene_node_name = f"{SCENE_NODE_NAME_PREFIX}{scene_node_index}"
        scene_node_label = scene_node_labels.get(scene_node_index)
        if scene_node_label is not None:
            scene_node_name = f"{scene_node_name}__{_name_suffix(scene_node_label)}"
        scene_node_obj = bpy.data.objects.new(scene_node_name, None)
        scene_node_obj.empty_display_type = "PLAIN_AXES"
        scene_node_obj[SCENE_NODE_INDEX_PROP] = scene_node_index

        scene_node_location = scene_node_locations.get(scene_node_index)
        if scene_node_location is not None:
            scene_node_obj.location = scene_node_location
        scene_node_yaw = scene_node_yaws.get(scene_node_index)
        if scene_node_yaw is not None and scene_node_yaw != 0:
            scene_node_obj.rotation_euler[2] = scene_node_yaw

        target_collection.objects.link(scene_node_obj)
        scene_node_objects.append(scene_node_obj)

    for child_scene_node_index, parent_scene_node_index in scene_node_parents.items():
        if child_scene_node_index >= len(scene_node_objects):
            continue
        if parent_scene_node_index >= len(scene_node_objects):
            continue
        if child_scene_node_index == parent_scene_node_index:
            continue

        scene_node_objects[child_scene_node_index].parent = scene_node_objects[
            parent_scene_node_index
        ]

    return scene_node_objects


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
    mesh_indices_to_scene_node_indices = _mesh_indices_to_scene_node_indices(
        three_d_objs_pc
    )
    scene_node_locations, scene_node_parents = _collect_scene_node_hierarchy(
        three_d_obj_pc.three_d_obj_db_pc
    )
    scene_node_locations_from_entries5, scene_node_yaws_from_entries5 = (
        _collect_scene_node_transforms_from_entries5(
            three_d_obj_pc.three_d_obj_db_pc,
            len(three_d_objs_pc.entries),
        )
    )
    for scene_node_index, scene_node_location in scene_node_locations_from_entries5.items():
        scene_node_locations[scene_node_index] = scene_node_location
    scene_node_labels = _collect_scene_node_labels(
        three_d_obj_pc.three_d_obj_db_pc,
        three_d_obj_pc.bininfo_bin,
        len(three_d_objs_pc.entries),
    )
    scene_node_objects = _create_scene_node_objects(
        target_collection,
        len(three_d_objs_pc.entries),
        scene_node_locations,
        scene_node_yaws_from_entries5,
        scene_node_parents,
        scene_node_labels,
    )

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
        mesh_name = f"{MESH_NAME_PREFIX}{i}"
        scene_node_index = mesh_indices_to_scene_node_indices[i]
        if scene_node_index is not None:
            scene_node_label = scene_node_labels.get(scene_node_index)
            if scene_node_label is not None:
                mesh_name = f"{mesh_name}__{_name_suffix(scene_node_label)}"
        mesh = bpy.data.meshes.new(mesh_name)
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj[MESH_INDEX_PROP] = i
        target_collection.objects.link(obj)
        if scene_node_index is not None:
            obj.parent = scene_node_objects[scene_node_index]

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
