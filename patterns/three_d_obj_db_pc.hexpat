import std.core;
import std.sys;
import fror;

// The string "3d objects scene definitions file is corrupted" associated with the `3dobjdb.pc`
// files implies that `3dobjdb.pc` files are 3d objects scene definitions files.

u32 THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY = 0x01;
u32 THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_02 = 0x02;
u32 THREE_D_OBJ_DB_PC_ENTRY_HAS_PIVOT_DATA = 0x04;
u32 THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_08 = 0x08;
u32 THREE_D_OBJ_DB_PC_ENTRY_HAS_FLAG10_ENTRIES = 0x10;

struct ThreeDObjDbPcEntryTransform {
    float floats[15];
    u32 data[23 - 15];
};

struct ThreeDObjDbPcEntryEntry2 {
    u32 a[7];
};

struct ThreeDObjDbPcEntryEntry3 {
    u32 a[3];
};

struct ThreeDObjDbPcEntryEntry4 {
    u32 a[2];
};

struct ThreeDObjDbPcEntryEntry5 {
    u32 scene_node_index;
    u16 scene_node_group;
    u16 c;
    Vec3f translation;
    float yaw;
    u32 h;
    u32 i;
    if (false) { // FIXME: Some functon argument controls this
        u32 j;
        u32 k;
    }
};

struct ThreeDObjDbPcEntryPivotData {
    float a[7];
};

struct ThreeDObjDbPcEntryFlag10Entry {
    u32 a[5];
};

struct ThreeDObjDbPcEntryEntry10 {
    u32 a[2];
};

struct ThreeDObjDbPcSceneNodeSubObjectBinding {
    // Index into bininfo.bin group 1 (sub-object names).
    u32 sub_object_name_index;
    // Index into this file's scene-node namespace.
    u32 scene_node_index;
};

struct ThreeDObjDbPcSceneNode {
    u32 flags = parent.flags;
    if (parent.flags & THREE_D_OBJ_DB_PC_SCENE_NODE_INDEX_ONLY) {
        u32 scene_node_index;
    } else {
        u32 scene_node_index;
        u16 a;
        padding[2];
        Vec3f translation;
        u32 e;
        u32 f;
        u32 g;
        u32 num_sub_object_bindings;
        ThreeDObjDbPcSceneNodeSubObjectBinding sub_object_bindings[num_sub_object_bindings];
        u32 num_child_nodes;
        ThreeDObjDbPcSceneNode child_nodes[num_child_nodes];
    }
};

fn all_eq(auto arr, auto val) {
    for (auto i = 0, i < std::core::member_count(arr), i += 1) {
        if (arr[i] != val) {
            return false;
        }
    }
    return true;
};

struct ThreeDObjDbPcEntry {
    s32 check[4];
    std::assert(all_eq(check, -1), "check != {-1, -1, -1, -1}");
    // Index into bininfo.bin group 0 (object shape names).
    u32 object_shape_name_index;
    u8 num_transforms;
    padding[3];
    ThreeDObjDbPcEntryTransform transforms[num_transforms];
    u32 num_entries2;
    ThreeDObjDbPcEntryEntry2 entries2[num_entries2];
    u32 num_entries3;
    ThreeDObjDbPcEntryEntry3 entries3[num_entries3];
    u8 num_entries4;
    padding[3];
    ThreeDObjDbPcEntryEntry4 entries4[num_entries4];
    u16 num_entries5;
    padding[2];
    ThreeDObjDbPcEntryEntry5 entries5[num_entries5];
    u32 flags;
    if (flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_PIVOT_DATA) {
        u32 num_entries6;
        ThreeDObjDbPcEntryPivotData entries6[num_entries6];
    }
    if (flags & THREE_D_OBJ_DB_PC_ENTRY_HAS_FLAG10_ENTRIES) {
        u32 num_entries7;
        ThreeDObjDbPcEntryFlag10Entry entries7[num_entries7];
    }
    if (flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_02) {
        // FIXME
        u32 fixme[-1];
    }
    if (flags & THREE_D_OBJ_DB_PC_ENTRY_FIXME_FLAG_08) {
        // FIXME
        u32 fixme[-1];
    }
    u8 num_lod_switch_distances;
    padding[3];
    float lod_switch_distances[num_lod_switch_distances];
    u32 scene_node_count;
    u32 scene_node_capacity;
    u8 num_active_scene_nodes;
    padding[3];
    u32 active_scene_node_indices[num_active_scene_nodes];
    u32 c;
    u16 d;
    padding[2];
    u16 e;
    padding[2];
    u8 num_entries10;
    padding[3];
    ThreeDObjDbPcEntryEntry10 entries10[num_entries10];
    u8 num_root_scene_nodes;
    padding[3];
    ThreeDObjDbPcSceneNode root_scene_nodes[num_root_scene_nodes];
};

struct ThreeDObjDbPcEntry3 {
    u16 a;
    u8 b;
    u8 c;
};

struct ThreeDObjDbPcEntry4 {
    u32 a[6];
};

struct ThreeDObjDbPcEntry5Entry {
    u32 a[6];
};

struct ThreeDObjDbPcEntry5 {
    u32 num_entries;
    ThreeDObjDbPcEntry5Entry entries[num_entries];
};

struct ThreeDObjDbPcEntry6 {
    u32 a;
    u32 b;
    u32 num_entries;
    u8 entries[num_entries];
    u32 c;
    u32 d[21];
};

struct ThreeDObjDbPc {
    u32 file_format_version;
    u32 num_entries;
    u32 c;
    u32 d;
    u32 e;
    u32 f;
    u32 g;
    u32 h;
    u32 i;
    u32 j;
    u32 k;
    u32 l;
    u32 m;
    u32 n;
    u32 o;
    u32 num_entries2;
    u32 q;
    if (file_format_version > 17) {
        u32 r;
        u32 s;
    }
    ThreeDObjDbPcEntry entries[num_entries];
    if (num_entries2 != 0) {
        u32 num_entries3;
        u32 num_entries4;
        u32 entries2[num_entries2];
        ThreeDObjDbPcEntry3 entries3[num_entries3];
        ThreeDObjDbPcEntry4 entries4[num_entries4];
    }
    u32 num_entries5;
    u32 t;
    ThreeDObjDbPcEntry5 entries5[num_entries5];
    u32 num_entries6;
    u32 u;
    ThreeDObjDbPcEntry6 entries6[num_entries6];
};

ThreeDObjDbPc three_d_obj_db_pc @ 0x0;

std::assert(std::mem::eof(), "Did not consume whole input");
