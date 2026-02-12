#pragma pattern_limit 0

import std.mem;
import std.sys;

struct PVSVisibleSectorRecord {
    // Visible sector grid coordinate.
    u8 visible_sector_x;
    // Visible sector grid coordinate.
    u8 visible_sector_z;
    // Packed signed delta-like byte used by runtime culling.
    s8 packed_delta_x;
    // Packed signed delta-like byte used by runtime culling.
    s8 packed_delta_z;
    // Packed visibility/class flags (high bits are commonly set).
    u8 visibility_flags;
};

struct PVSSectorEntry {
    // Source sector grid coordinate.
    u32 sector_x;
    // Source sector grid coordinate.
    u32 sector_z;
    // Small sector class/layer bucket.
    u32 sector_class;
    // Reserved/packed metadata. Commonly 0xDD fill in decompressed files.
    u8 reserved_metadata[0x1C];
    // Number of visible sector records that follow for this source sector.
    u32 num_visible_sectors;
    PVSVisibleSectorRecord visible_sectors[num_visible_sectors];
    std::mem::AlignTo<4>;
};

struct PVS {
    u32 num_sector_entries;
    // Matches sum(entries[*].num_visible_sectors).
    u32 total_visible_sector_records;
    PVSSectorEntry sector_entries[num_sector_entries];
};

PVS pvs @ 0x0;

std::assert(std::mem::eof(), "Did not consume whole input");
