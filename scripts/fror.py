import argparse
from dataclasses import dataclass
from io import BytesIO
import pathlib
import typing
import abc

from annotated_types import Len
from pydantic import BaseModel

from libfror.src.libfror.decompress import (
    compress_and_write,
    get_decompressed_binary_reader,
)
from libfror.src.libfror.binread import BinaryReader, BinaryWriter, Endianness
from libfror.src.libfror.types import (
    DBF,
    NPC,
    PCG,
    DDSHeader,
    DDSHeaderFourCC,
    PCGData,
    PCGEntry,
)


A = typing.TypeVar("A")


class Subcommand(typing.Protocol[A]):
    NAME: str

    Args: typing.Type[A]

    @classmethod
    def pre_setup(
        cls, subparsers: argparse._SubParsersAction[argparse.ArgumentParser]
    ) -> None:
        parser = subparsers.add_parser(cls.NAME)
        parser.set_defaults(klass=cls)
        cls.setup(parser)

    @classmethod
    @abc.abstractmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None: ...

    @classmethod
    def pre_execute(cls, args: argparse.Namespace) -> None:
        # TODO: WTF!?
        args_dict = args.__dict__
        del args_dict["subcommand"]
        del args_dict["klass"]
        cls.execute(cls.Args(**args_dict))

    @classmethod
    @abc.abstractmethod
    def execute(cls, args: A) -> None: ...


class CompressSubcommand(Subcommand):
    NAME = "compress"

    @dataclass
    class Args:
        decompressed: pathlib.Path
        compressed: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("decompressed", type=pathlib.Path)
        parser.add_argument("compressed", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        with open(args.decompressed, "rb") as decompressed:
            decompressed_data = decompressed.read()

            with open(args.compressed, "wb") as compressed:
                compress_and_write(decompressed_data, compressed)


class DecompressSubcommand(Subcommand):
    NAME = "decompress"

    @dataclass
    class Args:
        compressed: pathlib.Path
        decompressed: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("compressed", type=pathlib.Path)
        parser.add_argument("decompressed", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        with open(args.compressed, "rb") as compressed:
            decompressed_binary_reader = get_decompressed_binary_reader(compressed)
            decompressed_data = decompressed_binary_reader.read()

            with open(args.decompressed, "wb") as decompressed:
                decompressed.write(decompressed_data)


class ExtractDBFSubcommand(Subcommand):
    NAME = "xdbf"

    @dataclass
    class Args:
        dbf: pathlib.Path
        directory: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("dbf", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
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


class CreateDBFSubcommand(Subcommand):
    NAME = "cdbf"

    @dataclass
    class Args:
        directory: pathlib.Path
        dbf: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=pathlib.Path)
        parser.add_argument("dbf", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        files = dict(
            sorted(
                [
                    (str(path.relative_to(args.directory)), path.read_bytes())
                    for path in args.directory.rglob("*")
                    if not path.is_dir()
                ]
            )
        )
        dbf = DBF(files)
        with open(args.dbf, "wb") as dbf_file:
            binary_writer = BinaryWriter(dbf_file)
            DBF.binwrite(binary_writer, dbf, None, Endianness.LITTLE)


class ExtractNPCSubcommand(Subcommand):
    NAME = "xnpc"

    @dataclass
    class Args:
        npc: pathlib.Path
        directory: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("npc", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
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


class CreateNPCSubcommand(Subcommand):
    NAME = "cnpc"

    @dataclass
    class Args:
        directory: pathlib.Path
        npc: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=pathlib.Path)
        parser.add_argument("npc", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        # TODO: This doesn't order the files like in the original
        files = dict(
            sorted(
                [
                    (
                        str(path.relative_to(args.directory).with_suffix("")),
                        path.read_bytes(),
                    )
                    for path in args.directory.rglob("*")
                    if not path.is_dir()
                ]
            )
        )
        npc = NPC(files)
        with open(args.npc, "wb") as npc_file:
            binary_writer = BinaryWriter(npc_file)
            NPC.binwrite(binary_writer, npc, None, Endianness.LITTLE)


class PCGEntryManifest(BaseModel):
    name: str
    a: int
    b: int
    clip_width: int
    clip_height: int
    e: int
    f: int
    g: int
    h: int
    j: typing.Annotated[list[int], Len(min_length=84, max_length=84)]

    @staticmethod
    def from_pcg_entry(pcg_entry: PCGEntry) -> "PCGEntryManifest":
        return PCGEntryManifest(
            name=pcg_entry.name,
            a=pcg_entry.data.a,
            b=pcg_entry.data.b,
            clip_width=pcg_entry.data.clip_width,
            clip_height=pcg_entry.data.clip_height,
            e=pcg_entry.data.e,
            f=pcg_entry.data.f,
            g=pcg_entry.data.g,
            h=pcg_entry.data.h,
            j=list(pcg_entry.data.j),
        )

    def to_pcg_entry(self) -> PCGEntry:
        return PCGEntry(
            self.name,
            PCGData(
                self.a,
                self.b,
                0,
                0,
                self.clip_width,
                self.clip_height,
                self.e,
                self.f,
                self.g,
                self.h,
                bytes(self.j),
                b"",
            ),
        )


class PCGManifest(BaseModel):
    year_maybe: int
    checksum_or_time: int
    a: int
    entries: list[PCGEntryManifest]

    @staticmethod
    def from_pcg(pcg: PCG) -> "PCGManifest":
        return PCGManifest(
            year_maybe=pcg.year_maybe,
            checksum_or_time=pcg.checksum_or_time,
            a=pcg.a,
            entries=[
                PCGEntryManifest.from_pcg_entry(pcg_entry) for pcg_entry in pcg.entries
            ],
        )

    def to_pcg(self) -> PCG:
        return PCG(
            self.year_maybe,
            self.checksum_or_time,
            self.a,
            [pcg_entry_manifest.to_pcg_entry() for pcg_entry_manifest in self.entries],
        )


class ExtractPCGSubcommand(Subcommand):
    NAME = "xpcg"

    @dataclass
    class Args:
        pcg: pathlib.Path
        directory: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("pcg", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.pcg, "rb") as pcg:
            decompressed_binary_reader = get_decompressed_binary_reader(pcg)
            parsed_pcg = PCG.binread(
                decompressed_binary_reader, None, Endianness.LITTLE
            )

            pcg_manifest = PCGManifest.from_pcg(parsed_pcg)
            pcg_manifest_json = pcg_manifest.model_dump_json(indent=2, round_trip=True)

            (args.directory / "manifest.json").write_text(pcg_manifest_json)

            for entry in parsed_pcg.entries:
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

    @dataclass
    class Args:
        directory: pathlib.Path
        pcg: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=pathlib.Path)
        parser.add_argument("pcg", type=pathlib.Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        pcg_manifest_json = (args.directory / "manifest.json").read_text()
        pcg_manifest = PCGManifest.model_validate_json(pcg_manifest_json)
        pcg = pcg_manifest.to_pcg()

        for entry in pcg.entries:
            with open(args.directory / (entry.name + ".dds"), "rb") as dds:
                binary_reader = BinaryReader(dds)
                dds_header = DDSHeader.binread(binary_reader, None, Endianness.LITTLE)
                data = binary_reader.read()
                entry.data.width = dds_header.width
                entry.data.height = dds_header.height
                entry.data.data = data

        bytes_io = BytesIO()
        binary_writer = BinaryWriter(bytes_io)
        PCG.binwrite(binary_writer, pcg, None, Endianness.LITTLE)
        with open(args.pcg, "wb") as pcg_file:
            compress_and_write(bytes_io.getvalue(), pcg_file)


def main() -> None:
    parser = argparse.ArgumentParser(prog="Ford Racing Off Road")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    CompressSubcommand.pre_setup(subparsers)
    DecompressSubcommand.pre_setup(subparsers)
    ExtractDBFSubcommand.pre_setup(subparsers)
    CreateDBFSubcommand.pre_setup(subparsers)
    ExtractNPCSubcommand.pre_setup(subparsers)
    CreateNPCSubcommand.pre_setup(subparsers)
    ExtractPCGSubcommand.pre_setup(subparsers)
    CreatePCGSubcommand.pre_setup(subparsers)

    args = parser.parse_args()
    args.klass.pre_execute(args)


if __name__ == "__main__":
    main()
