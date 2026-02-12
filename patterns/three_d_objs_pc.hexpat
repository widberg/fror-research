#pragma array_limit 0

import std.core;
import std.mem;
import std.sys;

struct ObjectThing {
    u16 length; // Number of mesh descriptions to include starting with begin.
    u16 flags;
    u32 n;
    std::assert(n == 0, "n != 0");
    u32 begin; // Index in parent.parent.mesh_descriptors
    u32 p;
    std::assert(p == 0, "p != 0");
};

struct Object {
    float transformation[12]; // 3x4 row-major transformation matrix.
    ObjectThing lod_near;
    ObjectThing lod_far;
    u32 u;
    std::assert(u == 0, "u != 0");
    u32 v;
    std::assert(v == 0, "v != 0");
    Vec2f grid_translation;
};

fn calculate_sum(auto arr) {
    u32 sum = 0;
    for (u32 i = 0, i < std::core::member_count(arr), i += 1) {
        sum += arr[i].lod_near.length + arr[i].lod_far.length;
    }
    return sum;
};

fn calculate_size(u32 flags, s16 texture_index) {
    u32 size = 20;
    u8 cursor_0 = (flags >> 0) & 0xFF;
    u8 cursor_1 = (flags >> 8) & 0xFF;
    u8 cursor_2 = (flags >> 16) & 0xFF;
    u8 cursor_3 = (flags >> 24) & 0xFF;
    if ( (cursor_1 & 8) != 0 )
        size += 20;
    if ( (cursor_1 & 1) != 0 )
        size += 4;
    if ( texture_index == -1 || (cursor_0 & 2) != 0 || (cursor_0 & 4) != 0 )
        size += 4;
    if ( (cursor_0 & 8) != 0 )
        size += 4;
    if ( (cursor_0 & 0x10) != 0 )
        size += 4;
    if ( (cursor_0 & 0x40) != 0 )
        size += 4;
    if ( (cursor_0 & 0x80u) != 0 )
        size += 4;
    if ( (cursor_1 & 0x10) != 0 )
        size += 4;
    if ( (cursor_1 & 0x80u) != 0 )
        size += 4;
    if ( (cursor_2 & 1) != 0 )
        size += 4;
    return size;
};

struct MeshDescriptor {
    u32 flags;
    s16 texture_index; // The texture index in the DDS textures in textures.pc.
    u16 num_vertices;
    u16 num_triangle_strips;
    u8 data[calculate_size(flags, texture_index) - 4 - 2 - 2 - 2];
};

struct TriangleStrip {
    u16 num_indices;
    u16 indices[num_indices];
};

struct TriangleStripBuffer {
    u32 i = std::core::array_index();
    TriangleStrip triangle_strips[parent.mesh_descriptors[i].num_triangle_strips];
};

struct ThreeDObjsPc {
    u32 num_objects;
    padding[0xC]; // (cursor + 19) & 0xF0; WTF?
    Object objects[num_objects];
    u32 sum = calculate_sum(objects) [[export]];
    MeshDescriptor mesh_descriptors[sum];
    TriangleStripBuffer triangle_strip_buffers[sum];
};

ThreeDObjsPc three_d_objs_pc @ 0x0;

std::assert($ == std::mem::size(), "Did not consume whole input");
