import std.mem;
import std.sys;

struct PVSEntry {
    u32 a;
    u32 b;
    u32 c;
    u8 d[0x1C];
    u32 e;
    u8 f[5 * e];
    std::mem::AlignTo<4>;
};

struct PVS {
    u32 num_entries;
    u32 ignored;
    PVSEntry entries[num_entries];
};

PVS pvs @ 0x0;

std::assert(std::mem::eof(), "");
