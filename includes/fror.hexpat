import std.limits;
import std.string;

struct Vec3f {
    float x;
    float y;
    float z;
};

fn format_read_s16_float(auto u) {
    return float(u) / 0x800;
};

// FIXME: Is ImHex broken? This doesn't seem to run.
fn format_write_s16_float(ref str s) {
    return s16(std::string::parse_float(s) * 0x800);
};

using S16Float = s16 [[format_read("format_read_s16_float"), format_write("format_write_s16_float")]];

struct Vec2S16Float {
    S16Float x;
    S16Float y;
};

struct Luminance {
    u8 l;
} [[color(std::format("{0:02X}{0:02X}{0:02X}", l))]];
