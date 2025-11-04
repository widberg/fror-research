import std.mem;

struct FontsHdrEntry {
    char name[128];
    u32 a;
    u32 b;
    u32 c;
    u32 d;
    u32 e;
    u32 f;
    u32 g;
    u32 h;
    float i;
    u32 j;
    u32 k;
    u32 l;
    u32 m;
    u32 n;
    u32 o;
    u32 p;
    u32 q;
};

struct FontsHdr {
    FontsHdrEntry entries[while (!std::mem::eof())];
};

FontsHdr fonts_hdr @ 0x0;
