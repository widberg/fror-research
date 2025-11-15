#pragma array_limit 0

import std.core;
import std.mem;

struct ThreeDObjsPcEntry {
    float a[12];
    u16 the_first;
    u16 m;
    u32 n;
    u32 o;
    u32 p;
    u16 the_second;
    u16 q;
    u32 r;
    u32 s;
    u32 t;
    u32 u;
    u32 v;
    u32 w;
    u32 x;
};

fn calculate_sum(auto arr) {
    u32 sum = 0;
    for (u32 i = 0, i < std::core::member_count(arr), i += 1) {
        ThreeDObjsPcEntry elm = arr[i];
        sum += elm.the_first + elm.the_second;
    }
    return sum;
};

fn calculate_size(u32 flags, s16 w) {
    u32 size = 20;
    u8 cursor_0 = (flags >> 0) & 0xFF;
    u8 cursor_1 = (flags >> 8) & 0xFF;
    u8 cursor_2 = (flags >> 16) & 0xFF;
    u8 cursor_3 = (flags >> 24) & 0xFF;
    if ( (cursor_1 & 8) != 0 )
        size += 20;
    if ( (cursor_1 & 1) != 0 )
        size += 4;
    if ( w == -1 || (cursor_0 & 2) != 0 || (cursor_0 & 4) != 0 )
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

struct ThreeDObjsPcEntry2 {
    u32 flags;
    s16 w;
    u16 num_vertices;
    u32 a;
    u8 data[calculate_size(flags, w) - 4 - 2 - 2 - 4];
};

struct ThreeDObjsPcEntry3 {
    u32 i = std::core::array_index();
    ThreeDObjsPcEntry entry = parent.entries[i];
};

struct ThreeDObjsPc {
    u32 num_entries;
    padding[0xC]; // (cursor + 19) & 0xF0; WTF?
    ThreeDObjsPcEntry entries[num_entries];
    s32 sum = calculate_sum(entries) [[export]];
    if (sum > 0) {
        ThreeDObjsPcEntry2 entries2[sum];
    }
    ThreeDObjsPcEntry3 entries3[num_entries];
};

ThreeDObjsPc three_d_objs_pc @ 0x0;
