import argparse
import contextlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from string import Template
import typing
import abc
import subprocess
import tempfile

from annotated_types import Len
from pydantic import BaseModel, ConfigDict

from libfror.compression import (
    compress_and_write,
    get_decompressed_binary_reader,
    get_decompressed_binary_reader_from_path,
)
from libfror.binrw import BinaryReader, BinaryWriter, Endianness
from libfror.types import (
    DBF_FILE_FORMAT,
    BININFO_BIN_FILE_FORMAT,
    FONTS_HDR_FILE_FORMAT,
    FONTS_RAW_FILE_FORMAT,
    FONTS_DAT_FILE_FORMAT,
    GRADIENT_DAT_FILE_FORMAT,
    NPC_FILE_FORMAT,
    PCG_FILE_FORMAT,
    PVS_FILE_FORMAT,
    SPC_FILE_FORMAT,
    TEXTURES_PC_FILE_FORMAT,
    THREE_D_OBJ_DB_PC_FILE_FORMAT,
    THREE_D_OBJS_PC_FILE_FORMAT,
    DBF,
    NPC,
    PCG,
    DDSHeader,
    DDSPixelFormat,
    FileFormat,
    NPCFile,
    PCGData,
    PCGEntry,
    TexturesPc,
    TexturesPcEntry,
    TexturesPcEntry2,
    TexturesPcEntry3,
    TexturesPcEntry4,
    BininfoBin,
)

import logging


logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")


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
        args_dict = vars(args).copy()
        del args_dict["subcommand"]
        del args_dict["klass"]
        return cls.execute(cls.Args(**args_dict))

    @classmethod
    @abc.abstractmethod
    def execute(cls, args: A) -> None: ...


class CompressSubcommand(Subcommand):
    NAME = "compress"

    @dataclass
    class Args:
        decompressed: Path
        compressed: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("decompressed", type=Path)
        parser.add_argument("compressed", type=Path)

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
        compressed: Path
        decompressed: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("compressed", type=Path)
        parser.add_argument("decompressed", type=Path)

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
        dbf: Path
        directory: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("dbf", type=Path)
        parser.add_argument("directory", type=Path)

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
        directory: Path
        dbf: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=Path)
        parser.add_argument("dbf", type=Path)

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


class NPCFileManifest(BaseModel):
    flags: int

    model_config = ConfigDict(
        extra="forbid",
    )

    @staticmethod
    def from_npc_file(npc_file: NPCFile) -> "NPCFileManifest":
        return NPCFileManifest(
            flags=npc_file.flags,
        )

    def to_npc_file(self) -> NPCFile:
        return NPCFile(
            self.flags,
            b"",
        )


class NPCManifest(BaseModel):
    files: dict[str, NPCFileManifest]

    model_config = ConfigDict(
        extra="forbid",
    )

    @staticmethod
    def from_npc(npc: NPC) -> "NPCManifest":
        return NPCManifest(
            files={k: NPCFileManifest.from_npc_file(v) for k, v in npc.files.items()},
        )

    def to_npc(self) -> NPC:
        return NPC(
            {k: v.to_npc_file() for k, v in self.files.items()},
        )


class ExtractNPCSubcommand(Subcommand):
    NAME = "xnpc"

    @dataclass
    class Args:
        npc: Path
        directory: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("npc", type=Path)
        parser.add_argument("directory", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.npc, "rb") as npc:
            binary_reader = BinaryReader(npc)
            parsed_npc = NPC.binread(binary_reader, None, Endianness.LITTLE)

            npc_manifest = NPCManifest.from_npc(parsed_npc)

            npc_manifest_json = npc_manifest.model_dump_json(indent=2, round_trip=True)
            (args.directory / "manifest.json").write_text(npc_manifest_json)

            for name, file in parsed_npc.files.items():
                file_name = name + ".wav"
                file_path = args.directory / file_name
                file_path_directory = file_path.parent
                file_path_directory.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(file.data)


class CreateNPCSubcommand(Subcommand):
    NAME = "cnpc"

    @dataclass
    class Args:
        directory: Path
        npc: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=Path)
        parser.add_argument("npc", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        npc_manifest_json = (args.directory / "manifest.json").read_text()
        npc_manifest = NPCManifest.model_validate_json(npc_manifest_json)
        npc = npc_manifest.to_npc()

        for name, file in npc.files.items():
            file_name = name + ".wav"
            file_path = args.directory / file_name
            file.data = file_path.read_bytes()

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
    j: typing.Annotated[bytes, Len(min_length=84, max_length=84)]

    model_config = ConfigDict(
        extra="forbid",
        ser_json_bytes="hex",
        val_json_bytes="hex",
    )

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
            j=pcg_entry.data.j,
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
                self.j,
                b"",
            ),
        )


class PCGManifest(BaseModel):
    year_maybe: int
    checksum_or_time: int
    a: int
    entries: list[PCGEntryManifest]

    model_config = ConfigDict(
        extra="forbid",
    )

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
        pcg: Path
        directory: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("pcg", type=Path)
        parser.add_argument("directory", type=Path)

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
                        entry.data.width,
                        entry.data.height,
                        1,
                        DDSPixelFormat.from_bc2(),
                    )
                    DDSHeader.binwrite(
                        binary_writer, dds_header, None, Endianness.LITTLE
                    )
                    binary_writer.write(entry.data.data)


class CreatePCGSubcommand(Subcommand):
    NAME = "cpcg"

    @dataclass
    class Args:
        directory: Path
        pcg: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=Path)
        parser.add_argument("pcg", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        pcg_manifest_json = (args.directory / "manifest.json").read_text()
        pcg_manifest = PCGManifest.model_validate_json(pcg_manifest_json)
        pcg = pcg_manifest.to_pcg()

        for entry in pcg.entries:
            with open(args.directory / (entry.name + ".dds"), "rb") as dds:
                binary_reader = BinaryReader(dds)
                dds_header = DDSHeader.binread(binary_reader, None, Endianness.LITTLE)
                assert dds_header.ddspf == DDSPixelFormat.from_bc2()
                data = binary_reader.read()
                entry.data.width = dds_header.width
                entry.data.height = dds_header.height
                entry.data.data = data

        bytes_io = BytesIO()
        binary_writer = BinaryWriter(bytes_io)
        PCG.binwrite(binary_writer, pcg, None, Endianness.LITTLE)
        with open(args.pcg, "wb") as pcg_file:
            compress_and_write(bytes_io.getvalue(), pcg_file)


class TexturesPcEntryManifest(BaseModel):
    data: typing.Annotated[bytes, Len(min_length=0x400, max_length=0x400)]

    model_config = ConfigDict(
        extra="forbid",
        ser_json_bytes="hex",
        val_json_bytes="hex",
    )

    @staticmethod
    def from_textures_pc_entry(
        textures_pc_entry: TexturesPcEntry,
    ) -> "TexturesPcEntryManifest":
        return TexturesPcEntryManifest(data=textures_pc_entry.data)

    def to_textures_pc_entry(self) -> TexturesPcEntry:
        return TexturesPcEntry(self.data)


class TexturesPcEntry2Manifest(BaseModel):
    data: typing.Annotated[bytes, Len(min_length=0x40, max_length=0x40)]

    model_config = ConfigDict(
        extra="forbid",
        ser_json_bytes="hex",
        val_json_bytes="hex",
    )

    @staticmethod
    def from_textures_pc_entry2(
        textures_pc_entry2: TexturesPcEntry2,
    ) -> "TexturesPcEntry2Manifest":
        return TexturesPcEntry2Manifest(data=textures_pc_entry2.data)

    def to_textures_pc_entry2(self) -> TexturesPcEntry2:
        return TexturesPcEntry2(self.data)


class TexturesPcEntry3Manifest(BaseModel):
    data: typing.Annotated[bytes, Len(min_length=0x400, max_length=0x400)]

    model_config = ConfigDict(
        extra="forbid",
        ser_json_bytes="hex",
        val_json_bytes="hex",
    )

    @staticmethod
    def from_textures_pc_entry3(
        textures_pc_entry3: TexturesPcEntry3,
    ) -> "TexturesPcEntry3Manifest":
        return TexturesPcEntry3Manifest(data=textures_pc_entry3.data)

    def to_textures_pc_entry3(self) -> TexturesPcEntry3:
        return TexturesPcEntry3(self.data)


class TexturesPcEntry4Manifest(BaseModel):
    flags: int
    b: int
    name: str
    encoding: int
    e: float
    h: int
    i: int
    j: int

    model_config = ConfigDict(
        extra="forbid",
    )

    @staticmethod
    def from_textures_pc_entry4(
        textures_pc_entry4: TexturesPcEntry4,
    ) -> "TexturesPcEntry4Manifest":
        return TexturesPcEntry4Manifest(
            flags=textures_pc_entry4.flags,
            b=textures_pc_entry4.b,
            name=textures_pc_entry4.name,
            encoding=textures_pc_entry4.encoding,
            e=textures_pc_entry4.e,
            h=textures_pc_entry4.h,
            i=textures_pc_entry4.i,
            j=textures_pc_entry4.j,
        )

    def to_textures_pc_entry4(self) -> TexturesPcEntry4:
        return TexturesPcEntry4(
            self.flags,
            self.b,
            self.name,
            self.encoding,
            0,
            self.e,
            0,
            0,
            self.h,
            self.i,
            self.j,
            b"",
        )


class TexturePcManifest(BaseModel):
    entries: list[TexturesPcEntryManifest]
    entries2: list[TexturesPcEntry2Manifest]
    entries3: list[TexturesPcEntry3Manifest]
    b: int
    entries4: list[TexturesPcEntry4Manifest]

    model_config = ConfigDict(
        extra="forbid",
    )

    @staticmethod
    def from_textures_pc(textures_pc: TexturesPc) -> "TexturePcManifest":
        return TexturePcManifest(
            entries=[
                TexturesPcEntryManifest.from_textures_pc_entry(textures_pc_entry)
                for textures_pc_entry in textures_pc.entries
            ],
            entries2=[
                TexturesPcEntry2Manifest.from_textures_pc_entry2(textures_pc_entry2)
                for textures_pc_entry2 in textures_pc.entries2
            ],
            entries3=[
                TexturesPcEntry3Manifest.from_textures_pc_entry3(textures_pc_entry3)
                for textures_pc_entry3 in textures_pc.entries3
            ],
            b=textures_pc.b,
            entries4=[
                TexturesPcEntry4Manifest.from_textures_pc_entry4(textures_pc_entry4)
                for textures_pc_entry4 in textures_pc.entries4
            ],
        )

    def to_textures_pc(self) -> TexturesPc:
        return TexturesPc(
            [
                textures_pc_entry_manifest.to_textures_pc_entry()
                for textures_pc_entry_manifest in self.entries
            ],
            [
                textures_pc_entry2_manifest.to_textures_pc_entry2()
                for textures_pc_entry2_manifest in self.entries2
            ],
            [
                textures_pc_entry3_manifest.to_textures_pc_entry3()
                for textures_pc_entry3_manifest in self.entries3
            ],
            self.b,
            [
                textures_pc_entry4_manifest.to_textures_pc_entry4()
                for textures_pc_entry4_manifest in self.entries4
            ],
        )


class ExtractTexturesPcSubcommand(Subcommand):
    NAME = "xtpc"

    @dataclass
    class Args:
        textures_pc: Path
        directory: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("textures_pc", type=Path)
        parser.add_argument("directory", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        args.directory.mkdir(parents=True, exist_ok=True)

        with open(args.textures_pc, "rb") as textures_pc:
            decompressed_binary_reader = get_decompressed_binary_reader(textures_pc)
            parsed_tpc = TexturesPc.binread(
                decompressed_binary_reader, None, Endianness.LITTLE
            )

            textures_pc_manifest = TexturePcManifest.from_textures_pc(parsed_tpc)

            textures_pc_manifest_json = textures_pc_manifest.model_dump_json(
                indent=2, round_trip=True
            )
            (args.directory / "manifest.json").write_text(textures_pc_manifest_json)

            for i, textures_pc_entry4 in enumerate(parsed_tpc.entries4):
                path = args.directory / (f"{i}.{textures_pc_entry4.name}.dds")
                with open(path, "wb") as dds:
                    binary_writer = BinaryWriter(dds)
                    dds_header = DDSHeader(
                        textures_pc_entry4.width,
                        textures_pc_entry4.height,
                        textures_pc_entry4.num_mipmaps + 1,
                        textures_pc_entry4.get_dds_pixel_format(),
                    )
                    DDSHeader.binwrite(
                        binary_writer, dds_header, None, Endianness.LITTLE
                    )
                    binary_writer.write(textures_pc_entry4.data)


class CreateTexturesPcSubcommand(Subcommand):
    NAME = "ctpc"

    @dataclass
    class Args:
        directory: Path
        textures_pc: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=Path)
        parser.add_argument("textures_pc", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        textures_pc_manifest_json = (args.directory / "manifest.json").read_text()
        textures_pc_manifest = TexturePcManifest.model_validate_json(
            textures_pc_manifest_json
        )
        textures_pc = textures_pc_manifest.to_textures_pc()

        for i, textures_pc_entry4 in enumerate(textures_pc.entries4):
            path = args.directory / (f"{i}.{textures_pc_entry4.name}.dds")
            with open(path, "rb") as dds:
                binary_reader = BinaryReader(dds)
                dds_header = DDSHeader.binread(binary_reader, None, Endianness.LITTLE)
                assert dds_header.ddspf == textures_pc_entry4.get_dds_pixel_format()
                data = binary_reader.read()
                textures_pc_entry4.num_mipmaps = dds_header.mip_map_count - 1
                textures_pc_entry4.width = dds_header.width
                textures_pc_entry4.height = dds_header.height
                textures_pc_entry4.data = data

        bytes_io = BytesIO()
        binary_writer = BinaryWriter(bytes_io)
        TexturesPc.binwrite(binary_writer, textures_pc, None, Endianness.LITTLE)
        with open(args.textures_pc, "wb") as textures_pc_file:
            compress_and_write(bytes_io.getvalue(), textures_pc_file)


class BininfoBinManifest(BaseModel):
    groups: list[list[str]]

    model_config = ConfigDict(
        extra="forbid",
    )

    @staticmethod
    def from_bininfo_bin(bininfo_bin: BininfoBin) -> "BininfoBinManifest":
        return BininfoBinManifest(
            groups=bininfo_bin.groups,
        )

    def to_bininfo_bin(self) -> "BininfoBin":
        return BininfoBin(
            self.groups,
        )


class ExtractBininfoBinSubcommand(Subcommand):
    NAME = "xbib"

    @dataclass
    class Args:
        bininfo_bin: Path
        bininfo_bin_json: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("bininfo_bin", type=Path)
        parser.add_argument("bininfo_bin_json", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        with open(args.bininfo_bin, "rb") as bininfo_bin:
            binary_reader = BinaryReader(bininfo_bin)
            parsed_bininfo_bin = BininfoBin.binread(
                binary_reader, None, Endianness.LITTLE
            )

            bininfo_bin_manifest = BininfoBinManifest.from_bininfo_bin(
                parsed_bininfo_bin
            )
            pcg_manifest_json = bininfo_bin_manifest.model_dump_json(
                indent=2, round_trip=True
            )

            args.bininfo_bin_json.write_text(pcg_manifest_json)


class CreateBininfoBinSubcommand(Subcommand):
    NAME = "cbib"

    @dataclass
    class Args:
        bininfo_bin_json: Path
        bininfo_bin: Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("bininfo_bin_json", type=Path)
        parser.add_argument("bininfo_bin", type=Path)

    @classmethod
    def execute(cls, args: Args) -> None:
        bininfo_bin_manifest_json = args.bininfo_bin_json.read_text()
        bininfo_bin_manifest = BininfoBinManifest.model_validate_json(
            bininfo_bin_manifest_json
        )
        bininfo_bin = bininfo_bin_manifest.to_bininfo_bin()

        with open(args.bininfo_bin, "wb") as bininfo_bin_file:
            binary_writer = BinaryWriter(bininfo_bin_file)
            BininfoBin.binwrite(binary_writer, bininfo_bin, None, Endianness.LITTLE)


class ImHexValidateSubcommand(Subcommand):
    NAME = "imhex"

    @dataclass
    class Format:
        file_format: FileFormat
        pattern: str

        def command(
            self, imhex: Path, includes: Path, patterns: Path, decompressed_input: Path
        ) -> list[str | Path]:
            return [
                imhex,
                "--pl",
                "run",
                "--includes",
                includes,
                "--pattern",
                patterns / self.pattern,
                "--input",
                decompressed_input,
            ]

    FORMATS: list[Format] = [
        Format(DBF_FILE_FORMAT, "dbf.hexpat"),
        Format(BININFO_BIN_FILE_FORMAT, "bininfo_bin.hexpat"),
        Format(FONTS_HDR_FILE_FORMAT, "fonts_hdr.hexpat"),
        Format(FONTS_RAW_FILE_FORMAT, "fonts_raw.hexpat"),
        Format(FONTS_DAT_FILE_FORMAT, "fonts_dat.hexpat"),
        Format(GRADIENT_DAT_FILE_FORMAT, "gradient_dat.hexpat"),
        Format(NPC_FILE_FORMAT, "npc.hexpat"),
        Format(PCG_FILE_FORMAT, "pcg.hexpat"),
        Format(PVS_FILE_FORMAT, "pvs.hexpat"),
        Format(SPC_FILE_FORMAT, "spc.hexpat"),
        Format(TEXTURES_PC_FILE_FORMAT, "textures_pc.hexpat"),
        Format(THREE_D_OBJ_DB_PC_FILE_FORMAT, "three_d_obj_db_pc.hexpat"),
        Format(THREE_D_OBJS_PC_FILE_FORMAT, "three_d_objs_pc.hexpat"),
        # Format(THREE_D_OBJSP_PC_FILE_FORMAT, "three_d_objsp_pc.hexpat"),
    ]

    SEPARATOR: str = ","

    @dataclass
    class Args:
        fror_research: Path
        fror: Path
        verbose: bool
        imhex: Path
        formats: str

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("fror_research", type=Path)
        parser.add_argument("fror", type=Path)
        parser.add_argument("--verbose", action=argparse.BooleanOptionalAction)
        parser.add_argument("--imhex", type=Path, default="imhex")
        parser.add_argument(
            "--formats",
            type=str,
            default=cls.SEPARATOR.join(map(lambda f: f.file_format.name, cls.FORMATS)),
        )

    @classmethod
    def execute(cls, args: Args) -> None:
        includes = args.fror_research / "includes"
        patterns = args.fror_research / "patterns"
        formats = args.formats.split(cls.SEPARATOR)
        for format in cls.FORMATS:
            if format.file_format.name not in formats:
                continue
            if args.verbose:
                logging.debug(f"Processing format: {format.file_format.name}")
            for input in args.fror.glob(format.file_format.glob):
                if args.verbose:
                    logging.debug(f"Processing input: {input}")
                decompressed_input = input
                tmp_ctx = (
                    tempfile.TemporaryDirectory()
                    if format.file_format.compressed
                    else contextlib.nullcontext()
                )
                with tmp_ctx as tmp:
                    if format.file_format.compressed:
                        tmp_str = typing.cast(str, tmp)
                        with open(input, "rb") as f:
                            decompressed_binary_reader = get_decompressed_binary_reader(
                                f
                            )
                            decompressed_data = decompressed_binary_reader.read()
                            decompressed_input = Path(tmp_str) / "decompressed.bin"
                            decompressed_input.write_bytes(decompressed_data)
                    command = format.command(
                        args.imhex, includes, patterns, decompressed_input
                    )
                    if args.verbose:
                        logging.debug(command)

                    completed_process = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                    )

                    if (
                        completed_process.returncode != 0
                        or completed_process.stdout
                        or completed_process.stderr
                    ):
                        error = f"!!! ERROR: Failed to validate {input}"
                        if args.verbose:
                            error += f"\nreturncode: {completed_process.returncode}\nstdout: {completed_process.stdout}\nstderr: {completed_process.stderr}"
                        logging.critical(error)
                        raise SystemExit(completed_process.returncode)


class FileCompareSubcommand(Subcommand):
    NAME = "fcmp"

    @dataclass
    class Args:
        old: Path
        new: Path
        decompress: bool

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("old", type=Path)
        parser.add_argument("new", type=Path)
        parser.add_argument("--decompress", action=argparse.BooleanOptionalAction)

    @classmethod
    def execute(cls, args: Args) -> None:
        if args.decompress:
            old_bytes = get_decompressed_binary_reader_from_path(args.old).read()
            new_bytes = get_decompressed_binary_reader_from_path(args.new).read()
        else:
            old_bytes = args.old.read_bytes()
            new_bytes = args.new.read_bytes()

        for i, (old_byte, new_byte) in enumerate(zip(old_bytes, new_bytes)):
            if old_byte != new_byte:
                logging.critical(
                    f"old_bytes does not match new_bytes. {old_byte} != {new_byte} at 0x{i:X}."
                )
                raise SystemExit(1)


class FRORValidateSubcommand(Subcommand):
    NAME = "test"

    @dataclass
    class Format:
        file_format: FileFormat
        extract_subcommand: typing.Type[Subcommand]
        create_subcommand: typing.Type[Subcommand]
        file_compare: bool

        def commands(self, input_path: Path, tmp_path: Path) -> list[list[str | Path]]:
            underscored_input_path = re.sub(r"[^a-zA-Z0-9_-]", "_", str(input_path))
            intermediate_path = underscored_input_path + ".intermediate"
            intermediate2_path = underscored_input_path + ".intermediate2"
            extract_command: list[str | Path] = [
                "fror",
                self.extract_subcommand.NAME,
                input_path,
                tmp_path / intermediate_path,
            ]
            create_command: list[str | Path] = [
                "fror",
                self.create_subcommand.NAME,
                tmp_path / intermediate_path,
                tmp_path / underscored_input_path,
            ]
            check_command: list[str | Path] = []
            if self.file_compare:
                check_command = [
                    "fror",
                    "fcmp",
                    input_path,
                    tmp_path / underscored_input_path,
                ]
                if self.file_format.compressed:
                    check_command += ["--decompress"]
            else:
                check_command = [
                    "fror",
                    self.extract_subcommand.NAME,
                    tmp_path / underscored_input_path,
                    tmp_path / intermediate2_path,
                ]
            commands = [extract_command, create_command, check_command]
            return commands

    # Fake file format to test the compress/decompress subcommands
    COMPRESSED_FILE_FORMAT = FileFormat("compressed", PVS_FILE_FORMAT.glob, True)

    FORMATS: list[Format] = [
        Format(COMPRESSED_FILE_FORMAT, DecompressSubcommand, CompressSubcommand, True),
        Format(DBF_FILE_FORMAT, ExtractDBFSubcommand, CreateDBFSubcommand, False),
        Format(
            BININFO_BIN_FILE_FORMAT,
            ExtractBininfoBinSubcommand,
            CreateBininfoBinSubcommand,
            True,
        ),
        Format(NPC_FILE_FORMAT, ExtractNPCSubcommand, CreateNPCSubcommand, False),
        Format(PCG_FILE_FORMAT, ExtractPCGSubcommand, CreatePCGSubcommand, True),
        Format(
            TEXTURES_PC_FILE_FORMAT,
            ExtractTexturesPcSubcommand,
            CreateTexturesPcSubcommand,
            True,
        ),
    ]

    SEPARATOR: str = ","

    @dataclass
    class Args:
        fror: Path
        verbose: bool
        formats: str

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("fror", type=Path)
        parser.add_argument("--verbose", action=argparse.BooleanOptionalAction)
        parser.add_argument(
            "--formats",
            type=str,
            default=cls.SEPARATOR.join(map(lambda s: s.file_format.name, cls.FORMATS)),
        )

    @classmethod
    def execute(cls, args: Args) -> None:
        formats = args.formats.split(cls.SEPARATOR)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for format in cls.FORMATS:
                if format.file_format.name not in formats:
                    continue
                if args.verbose:
                    logging.debug(f"Processing format: {format.file_format.name}")
                for input in args.fror.glob(format.file_format.glob):
                    if args.verbose:
                        logging.debug(f"Processing input: {input}")
                    for command in format.commands(input, tmp_path):
                        if args.verbose:
                            logging.debug(command)

                        completed_process = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                        )

                        if (
                            completed_process.returncode != 0
                            or completed_process.stdout
                            or completed_process.stderr
                        ):
                            error = f"!!! ERROR: Failed to validate {input}"
                            if args.verbose:
                                error += f"\nreturncode: {completed_process.returncode}\nstdout: {completed_process.stdout}\nstderr: {completed_process.stderr}"
                            logging.critical(error)
                            raise SystemExit(completed_process.returncode)


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
    ExtractTexturesPcSubcommand.pre_setup(subparsers)
    CreateTexturesPcSubcommand.pre_setup(subparsers)
    ExtractBininfoBinSubcommand.pre_setup(subparsers)
    CreateBininfoBinSubcommand.pre_setup(subparsers)
    ImHexValidateSubcommand.pre_setup(subparsers)
    FileCompareSubcommand.pre_setup(subparsers)
    FRORValidateSubcommand.pre_setup(subparsers)

    args = parser.parse_args()
    args.klass.pre_execute(args)


if __name__ == "__main__":
    main()
