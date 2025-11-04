struct DBFEntry {
    char name[256];
    u32 offset;
    u32 compressed_size;
    u32 decompressed_size; // Zlib compression
    u8 data[compressed_size] @ 4 + parent.num_entries * (256 + 4 * 3) + offset;
};

struct DBF {
    u32 num_entries;
    DBFEntry entries[num_entries];
};

DBF dbf @ 0x0;
