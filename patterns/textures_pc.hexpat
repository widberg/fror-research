import std.sys;

struct TexturesPcEntry {
    u8 a[0x400];
};

struct TexturesPcEntry2 {
    u8 a[0x40];
};

struct TexturesPcEntry3 {
    u8 a[0x400];
};

enum TexturesPcEntry4Encoding : u32 {
    Bc1 = 1,
    Bc2 = 3,
};

fn calculate_size_internal(u32 width, u32 height, TexturesPcEntry4Encoding encoding) {
    match (encoding) {
        (TexturesPcEntry4Encoding::Bc1): return width * height / 2;
        (TexturesPcEntry4Encoding::Bc2): return width * height;
        (_): u8 error[-1]; // FIXME: Handle all encodings
    }
};

fn calculate_size(u32 width, u32 height, u32 num_mipmaps, TexturesPcEntry4Encoding encoding) {
    u32 size = 0;
    u32 calculated_num_mipmaps = 0;

    size += calculate_size_internal(width, height, encoding);
    width >>= 1;
    height >>= 1;
    while (width >= 4 && height >= 4 && num_mipmaps != 0) {
        size += calculate_size_internal(width, height, encoding);
        width >>= 1;
        height >>= 1;
        calculated_num_mipmaps += 1;
    }
    std::assert(calculated_num_mipmaps == num_mipmaps, "calculated_num_mipmaps != num_mipmaps");

    return size;
};

struct TexturesPcEntry4 {
    u32 flags;
    u32 b;
    u32 name_size;
    char name[name_size];
    TexturesPcEntry4Encoding encoding;
    u32 num_mipmaps;
    float e;
    u32 width;
    u32 height;
    u32 h;
    s32 i;
    s32 j;
    u8 data[calculate_size(width, height, num_mipmaps, encoding)];
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
    TexturesPcEntry4 entries4[num_entries4];
};

TexturesPc textures_pc @ 0x0;
