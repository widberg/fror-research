import type.color;

struct Gradient {
    char name[32];
    u32 num_pixels;
    type::RGBA8 pixels[num_pixels];
};

struct GradientDat {
    u32 num_gradients;
    Gradient gradients[num_gradients];
};

GradientDat gradient_dat @ 0x0;
