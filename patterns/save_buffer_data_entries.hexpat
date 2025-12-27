// To be run against FordORR.exe process memory
// In ImHex: File -> Open Other -> Process Memory -> FordORR.exe
// To be compared to the fields in for_racing.hexpat. For debugging.

import std.sys;

struct SaveBufferDataEntry {
    u32 valid;
    std::assert(valid == 1, "valid != 1");
    u32 dst;
    u32 size;
    u32 id;
    u32 version;
    std::assert(version == 0, "version != 0");
};

u32 save_buffer_data_entries_length @ 0x005F2B60;
SaveBufferDataEntry save_buffer_data_entries[save_buffer_data_entries_length] @ 0x0062FC6C;
