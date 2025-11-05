struct PCGData {
    u32 a;
    u32 b;
    u32 width;
    u32 height;
    u32 clip_width;
    u32 clip_height;
    u32 e;
    u32 f;
    u32 g;
    u32 h;
    u32 size;
    u8 j[84];
    u8 data[size]; // Bc2
};

struct PCGEntries {
    u32 offset;
    char name[0xC];
    PCGData data @ 0x00000080 + offset;
};

struct PCG {
    u32 num_entries;
    u32 year_maybe;
    u32 checksum_or_time;
    u32 a;
    PCGEntries entries[num_entries];
};

PCG pcg @ 0x0;
