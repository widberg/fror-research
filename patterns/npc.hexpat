struct NPCEntry {
    char name[64];
    // 0x1 - Set in some files but I haven't seen the game check for it
    // 0x2 - Related to 3D buffer "Cannot set a stereo wave file as a 3d buffer"
    // 0x4 - Sets an extra bit in some other flags that I don't see used
    u32 flags;
    u32 offset;
    u32 size;
    u8 data[size] @ 4 + parent.num_entries * (64 + 4 * 3) + offset;
};

struct NPC {
    u32 num_entries;
    NPCEntry entries[num_entries];
};

NPC npc @ 0x0;
