import argparse
import zlib
import struct


def read_u32(f):
    u32_struct = struct.Struct("<I")
    bs = f.read(u32_struct.size)
    (value,) = u32_struct.unpack(bs)
    return value


def main():
    parser = argparse.ArgumentParser(prog="PCG")
    parser.add_argument("pcg")
    parser.add_argument("decompressed")
    args = parser.parse_args()

    with open(args.pcg, "rb") as pcg:
        decompressed_size = read_u32(pcg)
        compressed_data = pcg.read()
        decompressed_data = zlib.decompress(compressed_data)
        assert len(decompressed_data) == decompressed_size

        with open(args.decompressed, "wb") as decompressed:
            decompressed.write(decompressed_data)


if __name__ == "__main__":
    main()
