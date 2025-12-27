#pragma name FORRacing
#pragma author widberg
#pragma description Ford Racing Off Road Save Editor

// TODO: Figure out more of the fields

import std.mem;
import std.string;
import std.sys;
import std.core;

fn get_id_for_save_section(str name, u32 size, u32 version) {
    u32 name_sum = 0;
    u32 name_len = std::string::length(name);
    for (u32 i = 0, i < name_len, i += 1) {
        name_sum += (i + 1) * name[i];
    }
    u32 id = version + name_sum - name_len * size;
    return id;
};

enum CampaignType : u32 {
    QUICK_RACE = 0,
    CAREER = 1,
    TOURNAMENT = 2
};

struct SaveSection_userdata_header_44_0 {
    u8 data[44];
};

enum SpeedUnits : u32 {
    KPH = 1,
    MPH = 2,
};

struct Car {
    u32 a;
    u32 b;
    padding[8];
    u8 data[0x18];
};

struct CarName {
    char16 name[32] [[hex::editor_export(std::format("Car Name {}", std::core::array_index()), "")]];
};

struct SaveSection_userdata_22596_0 {
    u32 format; // Check if equals 2
    u32 b;
    u32 c;
    CampaignType campaign_type;
    char name[32];
    char name2[32];
    u32 field_50;
    u32 track_select_group; // Used in "DATA\\GRAPHICS\\UI\\TRACKSEL\\GROUP%d\\GRAPHICS"
    u32 quick_race_money [[hex::editor_export("Quick Race Money", "")]]; // The next 3 fields can be viewed as an array where the index is campaign_type.
    u32 career_money [[hex::editor_export("Career Money", "")]];
    u32 tournament_money [[hex::editor_export("Tournament Money", "")]];
    padding[400];
    Car cars[36];
    padding[0x00001346-0x000007D0];
    CarName car_names[6];
    padding[18];
    u8 stuff[74];
    u8 stuff2[39];
    padding[0x00005580-0x00001549];
    u8 autosave [[hex::editor_export("Autosave", "0 - Disabled, 1 - Enabled")]];
    padding[7];
    SpeedUnits speed_units [[hex::editor_export("Speed Units", "Speed Units")]];
    padding[52];
    float music_volume [[hex::editor_export("Music Volume", "0 - 0%, 1 - 100%")]];
    float effects_volume [[hex::editor_export("Effects Volume", "0 - 0%, 1 - 100%")]];
    padding[4];
    u32 camera_distance [[hex::editor_export("Camera Distance", "1 - Fender, 2 - Chase, 14 - Far")]];
    padding[0x00005880-0x000055D0];
};

struct SaveSection_unlocking_item_unlocking_array_18_0 {
    u8 data[18];
};

struct SaveSection_unlocking_item_new_item_array_18_0 {
    u8 data[18];
};

struct SaveSection_unlocking_item_unlocking_array_36_0 {
    u8 data[36];
};

struct SaveSection_unlocking_item_new_item_array_36_0 {
    u8 data[36];
};

struct SaveSection_unlocking_item_unlocking_array_24_0 {
    u8 data[24];
};

struct SaveSection_unlocking_item_new_item_array_24_0 {
    u8 data[24];
};

struct SaveSection_unlocking_item_unlocking_array_34_0 {
    u8 data[34];
};

struct SaveSection_unlocking_item_new_item_array_34_0 {
    u8 data[34];
};

struct SaveSection {
    u32 id;
    u32 size;
    match (id) {
        (get_id_for_save_section("userdata_header", 44, 0)): SaveSection_userdata_header_44_0 data;
        (get_id_for_save_section("userdata", 22596, 0)): SaveSection_userdata_22596_0 data;
        (get_id_for_save_section("unlocking_item->unlocking_array", 18, 0)): SaveSection_unlocking_item_unlocking_array_18_0 data; // Career vehicles unloacked
        (get_id_for_save_section("unlocking_item->new_item_array", 18, 0)): SaveSection_unlocking_item_new_item_array_18_0 data; // Career vehicles new
        (get_id_for_save_section("unlocking_item->unlocking_array", 36, 0)): SaveSection_unlocking_item_unlocking_array_36_0 data; // Career/tournament map unlocked
        (get_id_for_save_section("unlocking_item->new_item_array", 36, 0)): SaveSection_unlocking_item_new_item_array_36_0 data; // Career/tournament map new
        (get_id_for_save_section("unlocking_item->unlocking_array", 24, 0)): SaveSection_unlocking_item_unlocking_array_24_0 data; // Arcade/multiplayer map unlocked
        (get_id_for_save_section("unlocking_item->new_item_array", 24, 0)): SaveSection_unlocking_item_new_item_array_24_0 data; // Arcade/multiplayer map new
        (get_id_for_save_section("unlocking_item->unlocking_array", 34, 0)): SaveSection_unlocking_item_unlocking_array_34_0 data;
        (get_id_for_save_section("unlocking_item->new_item_array", 34, 0)): SaveSection_unlocking_item_new_item_array_34_0 data;
        (_):  u8 data[size];
    }
    std::assert(sizeof(data) == size, "sizeof(data) != size");
};

struct FORRacing {
    SaveSection sections[while (!std::mem::eof() && std::mem::read_unsigned($, 8) != 0)];
};

FORRacing for_racing @ 0x0;
