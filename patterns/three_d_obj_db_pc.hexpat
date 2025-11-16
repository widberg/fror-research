// TODO: Finish this

struct ThreeDObjDbPcEntryEntry {
    float floats[15];
    u32 data[23-15];
};

struct ThreeDObjDbPcEntryEntry2 {
    u32 a[7];
};

struct ThreeDObjDbPcEntryEntry3 {
    u32 a[3];
};

struct ThreeDObjDbPcEntryEntry4 {
    u32 a[2];
};

struct ThreeDObjDbPcEntryEntry5 {
    u32 a[7];
    if (false) { // FIXME
        u32 b[2];
    }
};

struct ThreeDObjDbPcEntryEntry6 {
    float a[7];
};

struct ThreeDObjDbPcEntryEntry7 {
    u32 a[5];
};

struct ThreeDObjDbPcEntryEntry8 {
    float a;
};

struct ThreeDObjDbPcEntryEntry9 {
    u32 a;
};

struct ThreeDObjDbPcEntryEntry10 {
    u32 a[2];
};

struct ThreeDObjDbPcEntryEntry11Entry {
    u32 a;
    u32 b;
};

struct ThreeDObjDbPcEntryEntry11 {
    u32 flags = parent.flags;
    if (parent.flags & 0x01) {
        u16 a;
        padding[2];
    } else {
        u32 skip;
        u16 a;
        padding[2];
        u32 b;
        u32 c;
        u32 d;
        u32 e;
        u32 f;
        u32 g;
        u32 num_entries;
        ThreeDObjDbPcEntryEntry11Entry entries[num_entries];
        u32 num_entries2;
        ThreeDObjDbPcEntryEntry11 entries2[num_entries2];
    }
};

struct ThreeDObjDbPcEntry {
    s32 check[4];
    u32 index;
    u8 num_entries;
    padding[3];
    ThreeDObjDbPcEntryEntry entries[num_entries];
    u32 num_entries2;
    ThreeDObjDbPcEntryEntry2 entries2[num_entries2];
    u32 num_entries3;
    ThreeDObjDbPcEntryEntry3 entries3[num_entries3];
    u8 num_entries4;
    padding[3];
    ThreeDObjDbPcEntryEntry4 entries4[num_entries4];
    u16 num_entries5;
    padding[2];
    ThreeDObjDbPcEntryEntry5 entries5[num_entries5];
    u32 flags;
    if (flags & 0x04) {
        u32 num_entries6;
        ThreeDObjDbPcEntryEntry6 entries6[num_entries6];
    }
    if (flags & 0x10) {
        u32 num_entries7;
        ThreeDObjDbPcEntryEntry7 entries7[num_entries7];
    }
    if (flags & 0x02) {
        // FIXME
        u32 fixme[-1];
    }
    if (flags & 0x08) {
        // FIXME
        u32 fixme[-1];
    }
    u8 num_entries8;
    padding[3];
    ThreeDObjDbPcEntryEntry8 entries8[num_entries8];
    u32 a;
    u32 b;
    u32 num_entries9;
    ThreeDObjDbPcEntryEntry9 entries9[num_entries9];
    u32 c;
    u16 d;
    padding[2];
    u16 e;
    padding[2];
    u8 num_entries10;
    padding[3];
    ThreeDObjDbPcEntryEntry10 entries10[num_entries10];
    u8 num_entries11;
    padding[3];
    ThreeDObjDbPcEntryEntry11 entries11[num_entries11];
};

struct ThreeDObjDbPcTailEntry {
    u32 a[6];
};

struct ThreeDObjDbPcTailEntry2Entry {
    u8 a;
};

struct ThreeDObjDbPcTailEntry2 {
    u32 a;
    u32 b;
    u32 num_entries;
    ThreeDObjDbPcTailEntry2Entry entries[num_entries];
    u32 c;
    if (c != -1) {
        // FIXME: Do I actually have to do anything here?
    }
    u32 d[21]; // FIXME: Is that the right number?
};

struct ThreeDObjDbPcTail {
    u32 a;
    u32 num_entries;
    ThreeDObjDbPcTailEntry entries[num_entries];
    u32 b;
    u32 num_entries2;
    ThreeDObjDbPcTailEntry2 entries2[num_entries2];
};

struct ThreeDObjDbPc {
    u32 a;
    u32 num_entries;
    u32 c;
    u32 d;
    u32 e;
    u32 f;
    u32 g;
    u32 h;
    u32 i;
    u32 j;
    u32 k;
    u32 l;
    u32 m;
    u32 n;
    u32 o;
    u32 p;
    u32 q;
    if (a > 17) {
        u32 r;
        u32 s;
    }
    ThreeDObjDbPcEntry entries[num_entries];
    ThreeDObjDbPcTail tail;
};

ThreeDObjDbPc three_d_obj_db_pc @ 0x0;
