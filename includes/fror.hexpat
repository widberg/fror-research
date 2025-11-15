import std.limits;
import std.string;

struct Vec3f {
    float x;
    float y;
    float z;
};

fn format_read_u16_float(auto u) {
    return float(u) / std::limits::u16_max();
};

// FIXME: Is ImHex broken? This doesn't seem to run.
fn format_write_u16_float(ref str s) {
    return u16(std::string::parse_float(s) * std::limits::u16_max());
};

using U16Float = u16 [[format_read("format_read_u16_float"), format_write("format_write_u16_float")]];

struct Vec2U16Float {
    U16Float x;
    U16Float y;
};
