import re
import typing
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from .importer import (
    COLOR_ATTRIBUTE_NAME,
    MESH_INDEX_PROP,
    MESH_NAME_PREFIX,
    SOURCE_DIRECTORY_PROP,
)
from .modules.libfror.binrw import Endianness
from .modules.libfror.types import (
    ThreeDObjPc,
    TriangleStripBuffer,
    VertexBuffer,
    VertexColors,
    VertexNormals,
)

MESH_INDEX_NAME_RE = re.compile(rf"^{re.escape(MESH_NAME_PREFIX)}(\d+)")

UV: typing.TypeAlias = tuple[float, float]
RGBA: typing.TypeAlias = tuple[float, float, float, float]
Normal: typing.TypeAlias = tuple[float, float, float]
LoopValue = typing.TypeVar("LoopValue", UV, RGBA, Normal)


def _is_close_uv(a: UV, b: UV, epsilon: float) -> bool:
    return abs(a[0] - b[0]) <= epsilon and abs(a[1] - b[1]) <= epsilon


def _is_close_rgba(a: RGBA, b: RGBA, epsilon: float) -> bool:
    return (
        abs(a[0] - b[0]) <= epsilon
        and abs(a[1] - b[1]) <= epsilon
        and abs(a[2] - b[2]) <= epsilon
        and abs(a[3] - b[3]) <= epsilon
    )


def _is_close_normal(a: Normal, b: Normal, epsilon: float) -> bool:
    return (
        abs(a[0] - b[0]) <= epsilon
        and abs(a[1] - b[1]) <= epsilon
        and abs(a[2] - b[2]) <= epsilon
    )


def _extract_mesh_index(obj: bpy.types.Object) -> int | None:
    if MESH_INDEX_PROP in obj:
        try:
            index = int(obj[MESH_INDEX_PROP])
            if index >= 0:
                return index
        except (TypeError, ValueError):
            pass

    match = MESH_INDEX_NAME_RE.match(obj.name)
    if match is None:
        return None
    return int(match.group(1))


def _collect_per_vertex_loop_data(
    mesh: bpy.types.Mesh,
    loop_reader: typing.Callable[[int], LoopValue],
    fallback_values: list[LoopValue] | None,
    default_value: LoopValue,
    is_close: typing.Callable[[LoopValue, LoopValue, float], bool],
    epsilon: float = 1e-5,
) -> tuple[list[LoopValue], int, int]:
    num_vertices = len(mesh.vertices)
    per_vertex_values: list[LoopValue | None] = [None] * num_vertices
    num_inconsistent = 0

    for loop_index, loop in enumerate(mesh.loops):
        vertex_index = loop.vertex_index
        current_value = loop_reader(loop_index)
        previous_value = per_vertex_values[vertex_index]
        if previous_value is None:
            per_vertex_values[vertex_index] = current_value
        elif not is_close(previous_value, current_value, epsilon):
            num_inconsistent += 1

    num_missing = 0
    results: list[LoopValue] = []
    for i, value in enumerate(per_vertex_values):
        if value is None:
            num_missing += 1
            if fallback_values is not None and i < len(fallback_values):
                results.append(fallback_values[i])
            else:
                results.append(default_value)
        else:
            results.append(value)
    return results, num_inconsistent, num_missing


def _extract_vertex_colors(
    mesh: bpy.types.Mesh, previous_colors: list[RGBA]
) -> tuple[list[RGBA], int, int]:
    color_attr = mesh.color_attributes.get(COLOR_ATTRIBUTE_NAME)
    if color_attr is None:
        color_attr = mesh.color_attributes.active_color
    if color_attr is None:
        raise ValueError(
            f"Mesh '{mesh.name}' does not have a color attribute named '{COLOR_ATTRIBUTE_NAME}'."
        )

    if color_attr.domain == "POINT":
        if len(color_attr.data) != len(mesh.vertices):
            raise ValueError(
                f"Mesh '{mesh.name}' has POINT colors with unexpected length."
            )
        colors = [tuple(color_attr.data[i].color) for i in range(len(mesh.vertices))]
        return colors, 0, 0

    if color_attr.domain != "CORNER":
        raise ValueError(
            f"Mesh '{mesh.name}' color attribute domain '{color_attr.domain}' is unsupported."
        )

    colors, num_inconsistent, num_missing = _collect_per_vertex_loop_data(
        mesh,
        lambda loop_index: tuple(color_attr.data[loop_index].color),
        previous_colors if len(previous_colors) == len(mesh.vertices) else None,
        (1.0, 1.0, 1.0, 1.0),
        _is_close_rgba,
    )
    return colors, num_inconsistent, num_missing


def _extract_vertex_uvs(
    mesh: bpy.types.Mesh, previous_uvs: list[UV]
) -> tuple[list[UV], int, int]:
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise ValueError(f"Mesh '{mesh.name}' is missing an active UV layer.")
    if len(uv_layer.data) != len(mesh.loops):
        raise ValueError(
            f"Mesh '{mesh.name}' has UV layer data that does not match loop count."
        )

    uvs, num_inconsistent, num_missing = _collect_per_vertex_loop_data(
        mesh,
        lambda loop_index: tuple(uv_layer.data[loop_index].uv),
        previous_uvs if len(previous_uvs) == len(mesh.vertices) else None,
        (0.0, 0.0),
        _is_close_uv,
    )
    return uvs, num_inconsistent, num_missing


def _extract_vertex_normals(
    mesh: bpy.types.Mesh, previous_normals: list[Normal]
) -> tuple[list[Normal], int, int]:
    if len(mesh.corner_normals) != len(mesh.loops):
        raise ValueError(
            f"Mesh '{mesh.name}' has corner normals data that does not match loop count."
        )

    normals, num_inconsistent, num_missing = _collect_per_vertex_loop_data(
        mesh,
        lambda loop_index: tuple(mesh.corner_normals[loop_index].vector),
        previous_normals if len(previous_normals) == len(mesh.vertices) else None,
        (0.0, 0.0, 1.0),
        _is_close_normal,
    )
    return normals, num_inconsistent, num_missing


def _replace_geometry_from_object(
    obj: bpy.types.Object,
    previous_vertex_buffer: VertexBuffer,
) -> tuple[VertexBuffer, TriangleStripBuffer, list[str]]:
    if obj.type != "MESH":
        raise ValueError(f"Object '{obj.name}' is not a mesh.")

    if obj.mode == "EDIT":
        obj.update_from_editmode()

    mesh = obj.data
    assert isinstance(mesh, bpy.types.Mesh)

    positions = [tuple(vertex.co) for vertex in mesh.vertices]

    if all(len(polygon.vertices) == 3 for polygon in mesh.polygons):
        triangles = [list(polygon.vertices) for polygon in mesh.polygons]
    else:
        mesh.calc_loop_triangles()
        triangles = [
            list(loop_triangle.vertices) for loop_triangle in mesh.loop_triangles
        ]
    triangle_strip_buffer = TriangleStripBuffer.from_triangles_ccw(triangles)

    warnings: list[str] = []
    previous_vertex_buffer_z_up_v_up = previous_vertex_buffer.to_z_up_v_up()

    match previous_vertex_buffer_z_up_v_up.normals_or_colors:
        case VertexNormals(normals=previous_normals_z_up):
            normals, num_inconsistent, num_missing = _extract_vertex_normals(
                mesh, previous_normals_z_up
            )
            if num_inconsistent > 0:
                warnings.append(
                    f"{obj.name}: {num_inconsistent} normal conflicts on shared vertices; kept first value."
                )
            if num_missing > 0:
                warnings.append(
                    f"{obj.name}: {num_missing} vertices missing corner normal data; used fallback/default values."
                )
            normals_or_colors = VertexNormals(normals)
        case VertexColors(colors=previous_colors):
            colors, num_inconsistent, num_missing = _extract_vertex_colors(
                mesh, previous_colors
            )
            if num_inconsistent > 0:
                warnings.append(
                    f"{obj.name}: {num_inconsistent} color conflicts on shared vertices; kept first value."
                )
            if num_missing > 0:
                warnings.append(
                    f"{obj.name}: {num_missing} vertices missing corner color data; used fallback/default values."
                )
            normals_or_colors = VertexColors(colors)

    uvs = None
    if previous_vertex_buffer.uvs is not None:
        previous_uvs = previous_vertex_buffer_z_up_v_up.uvs
        assert previous_uvs is not None
        new_uvs, num_inconsistent, num_missing = _extract_vertex_uvs(mesh, previous_uvs)
        if num_inconsistent > 0:
            warnings.append(
                f"{obj.name}: {num_inconsistent} UV conflicts on shared vertices; kept first value."
            )
        if num_missing > 0:
            warnings.append(
                f"{obj.name}: {num_missing} vertices missing corner UV data; used fallback/default values."
            )
        uvs = new_uvs

    vertex_buffer = VertexBuffer.from_z_up_v_up(
        VertexBuffer(positions, normals_or_colors, uvs)
    )
    return vertex_buffer, triangle_strip_buffer, warnings


def export_fror_scene(
    context: bpy.types.Context,
    output_directory: Path,
    source_directory: Path | None = None,
    endianness: Endianness = Endianness.LITTLE,
) -> tuple[int, list[str]]:
    source_directory_str = None if source_directory is None else str(source_directory)
    if not source_directory_str and SOURCE_DIRECTORY_PROP in context.scene:
        source_directory_str = str(context.scene[SOURCE_DIRECTORY_PROP])
    if not source_directory_str:
        raise ValueError(
            "No source directory set. Import first or provide Source Directory."
        )

    source_directory = Path(source_directory_str)

    try:
        if source_directory.resolve() == output_directory.resolve():
            raise ValueError(
                "Output directory must be different from source directory."
            )
    except OSError:
        # resolve() can fail on some paths that do not exist yet
        if str(source_directory) == str(output_directory):
            raise ValueError(
                "Output directory must be different from source directory."
            )

    three_d_obj_pc = ThreeDObjPc.from_directory_path(source_directory, endianness)

    mesh_objects_by_index: dict[int, bpy.types.Object] = {}
    for obj in context.scene.objects:
        if obj.type != "MESH":
            continue
        index = _extract_mesh_index(obj)
        if index is None:
            continue
        if index in mesh_objects_by_index:
            raise ValueError(
                (
                    f"Duplicate mesh index {index} on objects "
                    f"'{mesh_objects_by_index[index].name}' and '{obj.name}'."
                )
            )
        mesh_objects_by_index[index] = obj

    three_d_objs_pc = three_d_obj_pc.three_d_objs_pc
    three_d_objsp_pc = three_d_obj_pc.three_d_objsp_pc

    updated_count = 0
    warning_messages: list[str] = []
    for i, (mesh_descriptor, old_vertex_buffer) in enumerate(
        zip(
            three_d_objs_pc.mesh_descriptors,
            three_d_objsp_pc.vertex_buffers,
            strict=True,
        )
    ):
        obj = mesh_objects_by_index.get(i)
        if obj is None:
            continue

        try:
            vertex_buffer, triangle_strip_buffer, warnings = (
                _replace_geometry_from_object(obj, old_vertex_buffer)
            )
        except Exception as exc:
            raise ValueError(
                f"Failed to export mesh {i} ('{obj.name}'): {exc}"
            ) from exc

        three_d_objsp_pc.vertex_buffers[i] = vertex_buffer
        three_d_objs_pc.triangle_strip_buffers[i] = triangle_strip_buffer
        mesh_descriptor.num_vertices = len(vertex_buffer.positions)
        mesh_descriptor.num_triangle_strips = len(triangle_strip_buffer.triangle_strips)

        updated_count += 1
        warning_messages.extend(warnings)

    three_d_obj_pc.to_directory_path(output_directory, endianness)
    return updated_count, warning_messages


class ExportFROR(Operator, ExportHelper):
    bl_idname = "fror_blender.export_fror"
    bl_label = "Export Ford Racing Off Road"
    bl_description = "Export modified Ford Racing Off Road 3dobj data"

    source_directory: bpy.props.StringProperty(
        name="Source Directory",
        description=(
            "Directory containing 3dobjdb.pc, 3dobjs.pc, 3dobjsp.pc, bininfo.bin, "
            "and textures.pc. Defaults to the last imported path."
        ),
        subtype="DIR_PATH",
    )  # pyright: ignore[reportInvalidTypeForm]

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        if not self.source_directory and SOURCE_DIRECTORY_PROP in context.scene:
            self.source_directory = str(context.scene[SOURCE_DIRECTORY_PROP])
        if not self.filepath and self.source_directory:
            source_path = Path(self.source_directory)
            self.filepath = str(source_path.with_name(source_path.name + "_export"))
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            updated_count, warning_messages = export_fror_scene(
                context,
                Path(self.filepath),
                Path(self.source_directory) if self.source_directory else None,
                Endianness.LITTLE,
            )
        except Exception as exc:
            self.report({"ERROR"}, f"{exc}")
            return {"CANCELLED"}

        for message in warning_messages[:10]:
            self.report({"WARNING"}, message)
        if len(warning_messages) > 10:
            self.report(
                {"WARNING"},
                f"... plus {len(warning_messages) - 10} more warnings.",
            )

        self.report(
            {"INFO"},
            f"Exported to '{self.filepath}' with {updated_count} mesh(es) updated.",
        )
        return {"FINISHED"}


def menu_func_export_fror(self, context: bpy.types.Context) -> None:
    self.layout.operator(ExportFROR.bl_idname, text="Ford Racing Off Road")


def register() -> None:
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_fror)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_fror)
