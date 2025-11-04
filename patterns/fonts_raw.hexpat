struct FontsRaw {
    u32 width;
    u32 height;
    u32 a;
    u32 b;
    u32 c;
    u8 data[width * height];
};

FontsRaw fonts_raw @ 0x0;
