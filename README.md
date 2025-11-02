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

### [Detect It Easy](https://github.com/horsicq/Detect-It-Easy)

```plaintext
PE32
    Operation system: Windows(XP)[I386, 32-bit, GUI]
    Linker: Watcom Linker(2.18*)[GUI32]
    Compiler: Watcom C/C++
    Language: C/C++
    (Heur)Protection: Generic[Custom DOS]
    (Heur)Licensing: Licensing[Strings]
```

### [signsrch](https://aluigi.altervista.org/mytoolz.htm)

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
