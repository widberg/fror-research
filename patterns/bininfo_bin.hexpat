import std.mem;

struct BininfoBinString {
    u32 offset;
    char data[] @ offset;
};

struct BininfoBinStringGroup {
    u32 num_strings;
    BininfoBinString strings[num_strings];
};

struct BininfoBin {
    u32 size;
    BininfoBinStringGroup groups[12];
};

BininfoBin bininfo_bin @ 0x0;
