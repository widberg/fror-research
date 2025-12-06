import argparse
import pathlib
import typing
import abc

from libfror.src.libfror.decompress import (
    compress_and_write,
    get_decompressed_binary_reader,
)
from libfror.src.libfror.binread import BinaryReader, BinaryWriter, Endianness
from libfror.src.libfror.types import DBF, NPC, PCG, DDSHeader, DDSHeaderFourCC


class Subcommand(typing.Protocol):
    NAME: str

    @classmethod
    def pre_setup(
        cls, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        parser = subparsers.add_parser(cls.NAME)
        parser.set_defaults(func=cls.execute)
        cls.setup(parser)

    @classmethod
    @abc.abstractmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None: ...

    @classmethod
    @abc.abstractmethod
    def execute(cls, args: argparse.Namespace) -> None: ...


class CompressSubcommand(Subcommand):
    NAME = "compress"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("decompressed", type=pathlib.Path)
        parser.add_argument("compressed", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None:
        with open(args.decompressed, "rb") as decompressed:
            decompressed_data = decompressed.read()

            with open(args.compressed, "wb") as compressed:
                compress_and_write(decompressed_data, compressed)


class DecompressSubcommand(Subcommand):
    NAME = "decompress"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("compressed", type=pathlib.Path)
        parser.add_argument("decompressed", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None:
        with open(args.compressed, "rb") as compressed:
            decompressed_binary_reader = get_decompressed_binary_reader(compressed)
            decompressed_data = decompressed_binary_reader.read()

            with open(args.decompressed, "wb") as decompressed:
                decompressed.write(decompressed_data)


class ExtractDBFSubcommand(Subcommand):
    NAME = "xdbf"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("dbf", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.dbf, "rb") as dbf:
            binary_reader = BinaryReader(dbf)
            parsed_dbf = DBF.binread(binary_reader, None, Endianness.LITTLE)

            for name, decompressed_data in parsed_dbf.files.items():
                file_path = args.directory / name
                file_path_directory = file_path.parent
                file_path_directory.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(decompressed_data)


class ExtractNPCSubcommand(Subcommand):
    NAME = "xnpc"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("npc", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.npc, "rb") as npc:
            binary_reader = BinaryReader(npc)
            parsed_npc = NPC.binread(binary_reader, None, Endianness.LITTLE)

            for name, decompressed_data in parsed_npc.files.items():
                file_name = name + ".wav"
                file_path = args.directory / file_name
                file_path_directory = file_path.parent
                file_path_directory.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(decompressed_data)


class ExtractPCGSubcommand(Subcommand):
    NAME = "xpcg"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("pcg", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.pcg, "rb") as pcg:
            decompressed_binary_reader = get_decompressed_binary_reader(pcg)
            parsed_pcg = PCG.binread(
                decompressed_binary_reader, None, Endianness.LITTLE
            )
            for entry in parsed_pcg.entries:
                print(entry.name)
                path = args.directory / (entry.name + ".dds")
                with open(path, "wb") as dds:
                    binary_writer = BinaryWriter(dds)
                    dds_header = DDSHeader(
                        entry.data.width, entry.data.height, 1, DDSHeaderFourCC.BC2
                    )
                    DDSHeader.binwrite(
                        binary_writer, dds_header, None, Endianness.LITTLE
                    )
                    binary_writer.write(entry.data.data)


class CreatePCGSubcommand(Subcommand):
    NAME = "cpcg"

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=pathlib.Path)
        parser.add_argument("pcg", type=pathlib.Path)

    @classmethod
    def execute(cls, args: argparse.Namespace) -> None: ...


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ford Racing Off Road")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    CompressSubcommand.pre_setup(subparsers)
    DecompressSubcommand.pre_setup(subparsers)
    ExtractDBFSubcommand.pre_setup(subparsers)
    ExtractNPCSubcommand.pre_setup(subparsers)
    ExtractPCGSubcommand.pre_setup(subparsers)
    CreatePCGSubcommand.pre_setup(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
