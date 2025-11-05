struct NPCEntry {
    char name[64];
    u32 compressed_size;
    u32 offset;
    u32 decompressed_size; // Zlib compression
    u8 data[decompressed_size] @ 4 + parent.num_entries * (64 + 4 * 3) + offset;
};

struct NPC {
    u32 num_entries;
    NPCEntry entries[num_entries];
};

NPC npc @ 0x0;
