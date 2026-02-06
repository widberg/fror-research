import std.core;
import std.limits;
import std.math;
import std.string;

struct Vec3f {
    float x;
    float y;
    float z;
};

fn format_read_s16_float(s16 v) {
    return float(v) / 0x800;
};

fn format_write_s16_float(str s) {
    return s16(std::string::parse_float(s) * 0x800);
};

using S16Float = s16 [[format_read("format_read_s16_float"), format_write("format_write_s16_float")]];

fn format_read_snorm8(s8 v) {
    if (v == -128) {
        return -1.0;
    }
    return float(v) / 127.0;
};

fn format_write_snorm8(str s) {
    float v = std::string::parse_float(s);
    if (v <= -1.0) {
        return s8(-128);
    }
    if (v >= 1.0) {
        return s8(127);
    }
    return s8(v * 127.0);
};

using SNorm8 = s8 [[format_read("format_read_snorm8"), format_write("format_write_snorm8")]];

struct Vec2S16Float {
    S16Float x;
    S16Float y;
};

struct Vec4SNorm8 {
    SNorm8 x;
    SNorm8 y;
    SNorm8 z;
    SNorm8 w;
};

fn calculate_vec4_snorm8_xyz_length(Vec4SNorm8 v) {
    float x = format_read_snorm8(v.x);
    float y = format_read_snorm8(v.y);
    float z = format_read_snorm8(v.z);
    return std::math::sqrt(x * x + y * y + z * z);
};

fn vec4_snorm8_xyz_length_is_unit_within_epsilon(Vec4SNorm8 v, float epsilon) {
    float length = calculate_vec4_snorm8_xyz_length(v);
    return length >= (1.0 - epsilon) && length <= (1.0 + epsilon);
};

fn all_vec4_snorm8_xyz_lengths_unit_within_epsilon(auto arr, float epsilon) {
    bool all_ok = true;
    for (auto i = 0, i < std::core::member_count(arr), i += 1) {
        if (!vec4_snorm8_xyz_length_is_unit_within_epsilon(arr[i], epsilon)) {
            float x = format_read_snorm8(arr[i].x);
            float y = format_read_snorm8(arr[i].y);
            float z = format_read_snorm8(arr[i].z);
            float w = format_read_snorm8(arr[i].w);
            float length = calculate_vec4_snorm8_xyz_length(arr[i]);
            std::print(
                "Vec4SNorm8 length mismatch @ 0x{:X}: ({}, {}, {}, {}), length={}, epsilon={}",
                addressof(arr[i]),
                x,
                y,
                z,
                w,
                length,
                epsilon
            );
            all_ok = false;
        }
    }
    return all_ok;
};

fn all_vec4_snorm8_w_is_zero(auto arr) {
    bool all_ok = true;
    for (auto i = 0, i < std::core::member_count(arr), i += 1) {
        float w = format_read_snorm8(arr[i].w);
        if (w != 0.0) {
            std::print(
                "Vec4SNorm8 w mismatch @ 0x{:X}: w={}",
                addressof(arr[i]),
                w
            );
            all_ok = false;
        }
    }
    return all_ok;
};

struct Luminance {
    u8 l;
} [[color(std::format("{0:02X}{0:02X}{0:02X}", l))]];
