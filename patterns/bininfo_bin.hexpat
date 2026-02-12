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
    BininfoBinStringGroup object_shape_names;
    BininfoBinStringGroup sub_object_names;
    BininfoBinStringGroup camera_names;
    BininfoBinStringGroup texture_livery_sets;
    BininfoBinStringGroup reserved4;
    BininfoBinStringGroup scene_link_type_names;
    BininfoBinStringGroup light_names;
    BininfoBinStringGroup surface_or_zone_types;
    BininfoBinStringGroup reserved8;
    BininfoBinStringGroup effect_attachment_names;
    BininfoBinStringGroup reserved10;
    BininfoBinStringGroup damage_names;
};

BininfoBin bininfo_bin @ 0x0;
