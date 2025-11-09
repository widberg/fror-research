struct TexturesPcEntry {
    u8 a[0x400];
};

struct TexturesPcEntry2 {
    u8 a[0x40];
};

struct TexturesPcEntry3 {
    u8 a[0x400];
};

struct TexturesPcEntry4 {
    u32 a;
    u32 b;
    u32 name_size;
    char name[name_size];
    u32 c;
    u32 d;
    float e;
    u32 f;
    u32 g;
    u32 h;
};

struct TexturesPc {
    u32 num_entries;
    u32 num_entries2;
    u32 num_entries3;
    TexturesPcEntry entries[num_entries];
    TexturesPcEntry2 entries2[num_entries2];
    TexturesPcEntry3 entries3[num_entries3];
    u32 num_entries4;
    u32 b;
    TexturesPcEntry4 entries4[1 /* num_entries4 */];
};

TexturesPc textures_pc @ 0x0;
