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
    char16 name[32];
};

struct FORRacing {
    u32 b;
    u32 c;
    char name[];
    $ = 0x00000048;
    u32 number_of_cars;
    char name2[];
    padding[22];
    char name3[];
    $ = 0x00000098;
    u32 money;
    $ = 0x00000230;
    Car cars[36];
    $ = 0x00000D88;
    u32 a;
    $ = 0x00001346;
    CarName car_names[6];
    $ = 0x5580;
    u8 autosave;
    padding[7];
    SpeedUnits speed_units;
    padding[52];
    float music_volume;
    float effects_volume;
    padding[4];
    u32 camera_distance; // 2 - chase, E - far, 1 - fender
};

FORRacing for_racing @ 0x0;
