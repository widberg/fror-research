struct SPCEntry {
    char name[64]; // Garbage after null
};

struct SPC {
    u32 num_entries;
    SPCEntry entries[num_entries];
};

SPC spc @ 0x0;
