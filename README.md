# Ford Racing Off Road Research

Information that might be useful for modding Ford Racing Off Road (2008) by Razorworks.

## External Wikis

* [Ford Racing Off Road on PCGamingWiki](https://www.pcgamingwiki.com/wiki/Ford_Racing:_Off_Road)
* [Ford Racing Off Road on MobyGames](https://www.mobygames.com/game/44393/ford-racing-off-road/)
* [Ford Racing Off Road on Wikipedia](https://en.wikipedia.org/wiki/Off_Road_(video_game))
* [Ford Racing 3 Fandom Wiki](https://fordracing3.fandom.com/wiki/Ford_Racing_3_Wiki)
* [Ford Racing Off Road on SteamDB](https://steamdb.info/app/315740/)
* [Ford Racing Off Road on speedrun.com](https://www.speedrun.com/fordracing_offroad)
* [[PS2] Ford Racing 2 USA Beta [SLUS-20788] [2003-07-28].7z (1.3 MB) on debugging.games](https://debugging.games/)

## Prior Work

* [Ford Racing Off Road on GameBanana](https://gamebanana.com/games/8561)
* [Ford Racing 3 Modding page on Fandom Wiki](https://fordracing3.fandom.com/wiki/Modding)
* [Ford Racing Off Road on WSGF](https://www.wsgf.org/dr/ford-racing-road/en)

## Notes

### Files

#### Extensions

| Extension | Type |
| --- | --- |
| .at3 | [ATRAC](https://en.wikipedia.org/wiki/ATRAC)3+ (Adaptive TRansform Acoustic Coding 3+) |
| .pse | Particle Effects/text |
| .ui | ui/text |
| .wav | [Waveform Audio File Format (WAVE)](https://en.wikipedia.org/wiki/WAV) |
| .wiv | Uncompressed [WAVE](https://en.wikipedia.org/wiki/WAV) |
| .WMA | [Windows Media Audio](https://en.wikipedia.org/wiki/Windows_Media_Audio) |

### Signatures

#### [Detect It Easy](https://github.com/horsicq/Detect-It-Easy)

`FordORR.exe`

```plaintext
PE32
    Operation system: Windows(XP)[I386, 32-bit, GUI]
    Linker: Watcom Linker(2.18*)[GUI32]
    Compiler: Watcom C/C++
    Language: C/C++
    (Heur)Protection: Generic[Custom DOS]
    (Heur)Licensing: Licensing[Strings]
```

#### [signsrch](https://aluigi.altervista.org/mytoolz.htm)

`signsrch -e FordORR.exe`

```plaintext
- open file "FordORR.exe"
- 2250240 bytes allocated
- load signatures
- open file C:\Users\widberg\signsrch\signsrch.sig
- 3079 signatures in the database
- start 12 threads
- start signatures scanning:

  offset   num  description [bits.endian.size]
  --------------------------------------------
  0040b6ad 3048 DMC compression [32.le.16&]
  0047f5e0 1038 padding used in hashing algorithms (0x80 0 ... 0) [..64]
  005ee1e8 2190 CRC32_DS [32.le.68&]
  005eef8c 648  CRC-32-IEEE 802.3 [crc32.0xedb88320 lenorev 1.1024]
  005eef8c 641  CRC-32-IEEE 802.3 [crc32.0x04c11db7 le rev int_min.1024]
  005ef43c 2294 zinflate_lengthExtraBits [32.le.116]
  005ef4ad 2304 zinflate_distanceExtraBits [32.be.120]
  005ef4b0 2303 zinflate_distanceExtraBits [32.le.120]
  005efa80 1086 Zlib dist_code [..512]
  005efc80 1087 Zlib length_code [..256]
  005efd80 1089 Zlib base_length [32.le.116]
  005efdf4 1091 Zlib base_dist [32.le.120]
  005efeec 2289 zinflate_lengthStarts [16.le.58]
  005eff68 2296 zinflate_distanceStarts [16.le.60]
  005effa4 2301 zinflate_distanceExtraBits [16.le.60]
  005fe930 3038 unlzx table_three [32.le.64]
  0060814c 3051 compression algorithm seen in the game DreamKiller [32.be.12&]

- 17 signatures found in the file in 1 seconds
```

### [dumpbin](https://learn.microsoft.com/en-us/cpp/build/reference/dumpbin-reference?view=msvc-170)

`dumpbin /HEADERS FordORR.exe`

<details>

```plaintext
Microsoft (R) COFF/PE Dumper Version 14.44.35215.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file FordORR.exe

PE signature found

File Type: EXECUTABLE IMAGE

FILE HEADER VALUES
             14C machine (x86)
               5 number of sections
        47B22E96 time date stamp Tue Feb 12 18:41:10 2008
               0 file pointer to symbol table
               0 number of symbols
              E0 size of optional header
             182 characteristics
                   Executable
                   Bytes reversed
                   32 bit word machine

OPTIONAL HEADER VALUES
             10B magic # (PE32)
            2.18 linker version
          1B4A00 size of code
           57400 size of initialized data
          4BBE00 size of uninitialized data
          1A9AD0 entry point (005A9AD0)
            1000 base of code
          1B6000 base of data
          400000 image base (00400000 to 00AE3FFF)
            1000 section alignment
             200 file alignment
            1.11 operating system version
            0.00 image version
            4.00 subsystem version
               0 Win32 version
          6E4000 size of image
             400 size of headers
               0 checksum
               2 subsystem (Windows GUI)
               0 DLL characteristics
           1F400 size of stack reserve
           10000 size of stack commit
            2000 size of heap reserve
            1000 size of heap commit
               0 loader flags
              10 number of directories
               0 [       0] RVA [size] of Export Directory
          1B6000 [    165A] RVA [size] of Import Directory
               0 [       0] RVA [size] of Resource Directory
               0 [       0] RVA [size] of Exception Directory
               0 [       0] RVA [size] of Certificates Directory
          6CA000 [   19328] RVA [size] of Base Relocation Directory
               0 [       0] RVA [size] of Debug Directory
               0 [       0] RVA [size] of Architecture Directory
               0 [       0] RVA [size] of Global Pointer Directory
               0 [       0] RVA [size] of Thread Storage Directory
               0 [       0] RVA [size] of Load Configuration Directory
               0 [       0] RVA [size] of Bound Import Directory
               0 [       0] RVA [size] of Import Address Table Directory
               0 [       0] RVA [size] of Delay Import Directory
               0 [       0] RVA [size] of COM Descriptor Directory
               0 [       0] RVA [size] of Reserved Directory


SECTION HEADER #1
    AUTO name
  1B49EA virtual size
    1000 virtual address (00401000 to 005B59E9)
  1B4A00 size of raw data
     400 file pointer to raw data (00000400 to 001B4DFF)
       0 file pointer to relocation table
       0 file pointer to line numbers
       0 number of relocations
       0 number of line numbers
60000020 flags
         Code
         Execute Read

SECTION HEADER #2
  .idata name
    165A virtual size
  1B6000 virtual address (005B6000 to 005B7659)
    1800 size of raw data
  1B4E00 file pointer to raw data (001B4E00 to 001B65FF)
       0 file pointer to relocation table
       0 file pointer to line numbers
       0 number of relocations
       0 number of line numbers
C0000040 flags
         Initialized Data
         Read Write

SECTION HEADER #3
  DGROUP name
   55B8C virtual size
  1B8000 virtual address (005B8000 to 0060DB8B)
   55C00 size of raw data
  1B6600 file pointer to raw data (001B6600 to 0020C1FF)
       0 file pointer to relocation table
       0 file pointer to line numbers
       0 number of relocations
       0 number of line numbers
C0000040 flags
         Initialized Data
         Read Write

SECTION HEADER #4
    .bss name
       0 virtual size
  20E000 virtual address
  4BBE00 size of raw data
       0 file pointer to raw data
       0 file pointer to relocation table
       0 file pointer to line numbers
       0 number of relocations
       0 number of line numbers
C0000080 flags
         Uninitialized Data
         Read Write

SECTION HEADER #5
  .reloc name
       0 virtual size
  6CA000 virtual address
   19400 size of raw data
  20C200 file pointer to raw data (0020C200 to 002255FF)
       0 file pointer to relocation table
       0 file pointer to line numbers
       0 number of relocations
       0 number of line numbers
42000040 flags
         Initialized Data
         Discardable
         Read Only

  Summary

      4BC000 .bss
        2000 .idata
       1A000 .reloc
      1B5000 AUTO
       56000 DGROUP
```

</details>
