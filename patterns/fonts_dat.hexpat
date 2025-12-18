#pragma pattern_limit 0

import std.mem;
import std.sys;

import fror;

struct Character<auto A, auto F> {
    u32 unicode_codepoint;
    u32 width;
    u32 height;
    s32 d;
    u32 other_width;
    s32 f;
    u32 other_height;
    Luminance data[(width+2*A)*(height+2*A)];
    if ((F & 0x1) != 0) {
        Luminance data2[(width+2*A)*(height+2*A)];
    }
    if ((F & 0x2) != 0) {
        Luminance data3[(width+2*A)*(height+2*A)];
    }
};

u32 SENTINEL @ 0x0;

struct CharacterGroup<auto A, auto F> {
    Character<A, F> _9633;
    std::assert(_9633.unicode_codepoint == SENTINEL, "_9633.unicode_codepoint != SENTINEL");
    Character<A, F> characters[while (!std::mem::eof() && std::mem::read_unsigned($, 4) != SENTINEL)];
};

struct FontsDat {
    CharacterGroup<1, 0> character_group;
    CharacterGroup<2, 1> character_group2;
    CharacterGroup<2, 1> character_group3;
    CharacterGroup<2, 1> character_group4;
    CharacterGroup<1, 0> character_group5;
    CharacterGroup<1, 0> character_group6;
    CharacterGroup<2, 1> character_group7;
    CharacterGroup<2, 1> character_group8;
    CharacterGroup<2, 1> character_group9;
};

FontsDat fonts_dat @ 0x0;

std::assert(std::mem::eof(), "Did not consume whole input");
