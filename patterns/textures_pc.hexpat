import std.sys;
import std.mem;
import std.io;

struct TexturesPcEntry {
    u8 a[0x400];
};

struct TexturesPcEntry2 {
    u8 a[0x40];
};

struct TexturesPcEntry3 {
    u8 a[0x400];
};

fn calculate_size_internal(u32 width, u32 height, u32 encoding, u32 flags) {
    if (encoding == 1) {
        encoding = 5;
    }
    if ((flags & 0x10) != 0) {
        match (encoding) {
            (2 | 3): return width * height * 4; // RGBA
            (5): return width * height * 3; // RGB
        }
    } else {
        match (encoding) {
            (2 | 5): return width * height / 2; // Bc1
            (3): return width * height; // Bc2
        }
    }
    std::assert(false, std::format("Unhandled encoding: {}, flags: 0{:X}", encoding, flags));
};

fn calculate_size(u32 width, u32 height, u32 num_mipmaps, u32 encoding, u32 flags) {
    u32 size = 0;
    u32 calculated_num_mipmaps = 0;

    size += calculate_size_internal(width, height, encoding, flags);
    width >>= 1;
    height >>= 1;
    while (width >= 4 && height >= 4 && num_mipmaps != 0) {
        size += calculate_size_internal(width, height, encoding, flags);
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
    u32 encoding;
    u32 num_mipmaps;
    float e;
    u32 width;
    u32 height;
    u32 h;
    s32 i;
    s32 j;
    u8 data[calculate_size(width, height, num_mipmaps, encoding, flags)];
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

std::assert(std::mem::eof(), "Did not consume whole input");
