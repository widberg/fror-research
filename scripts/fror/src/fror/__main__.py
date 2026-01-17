import argparse
import contextlib
from dataclasses import dataclass
from io import BytesIO
import pathlib
import typing
import abc
import subprocess
import tempfile

from annotated_types import Len
from pydantic import BaseModel, ConfigDict

from libfror.compression import (
    compress_and_write,
    get_decompressed_binary_reader,
)
from libfror.binrw import BinaryReader, BinaryWriter, Endianness
from libfror.types import (
    DBF,
    NPC,
    PCG,
    DDSHeader,
    DDSPixelFormat,
    PCGData,
    PCGEntry,
    TexturesPc,
    TexturesPcEntry,
    TexturesPcEntry2,
    TexturesPcEntry3,
    TexturesPcEntry4,
    BininfoBin,
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
        args_dict = vars(args).copy()
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
    j: typing.Annotated[bytes, Len(min_length=84, max_length=84)]

    model_config = ConfigDict(
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
        textures_pc: pathlib.Path
        directory: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("textures_pc", type=pathlib.Path)
        parser.add_argument("directory", type=pathlib.Path)

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
        directory: pathlib.Path
        textures_pc: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("directory", type=pathlib.Path)
        parser.add_argument("textures_pc", type=pathlib.Path)

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
        bininfo_bin: pathlib.Path
        bininfo_bin_json: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("bininfo_bin", type=pathlib.Path)
        parser.add_argument("bininfo_bin_json", type=pathlib.Path)

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
        bininfo_bin_json: pathlib.Path
        bininfo_bin: pathlib.Path

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("bininfo_bin_json", type=pathlib.Path)
        parser.add_argument("bininfo_bin", type=pathlib.Path)

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
        glob: str
        pattern: str
        compressed: bool

    FORMATS: dict[str, Format] = {
        "dbf": Format("data/**/*.dbf", "dbf.hexpat", False),
        "bininfo_bin": Format("data/**/bininfo.bin", "bininfo_bin.hexpat", False),
        "fonts_hdr": Format("data/**/fonts.hdr", "fonts_hdr.hexpat", False),
        "fonts_raw": Format("data/**/fonts/*.raw", "fonts_raw.hexpat", False),
        "fonts_dat": Format("data/**/fonts.dat", "fonts_dat.hexpat", False),
        "gradient_dat": Format("data/**/gradient.dat", "gradient_dat.hexpat", False),
        "npc": Format("data/**/*.npc", "npc.hexpat", False),
        "pcg": Format("data/**/*.pcg", "pcg.hexpat", True),
        "pvs": Format("data/**/*.pvs", "pvs.hexpat", True),
        "spc": Format("data/**/*.spc", "spc.hexpat", False),
        "textures_pc": Format("data/**/textures.pc", "textures_pc.hexpat", True),
        "3dobjdb_pc": Format("data/**/3dobjdb.pc", "three_d_obj_db_pc.hexpat", False),
        "3dobjs_pc": Format("data/**/3dobjs.pc", "three_d_objs_pc.hexpat", True),
        # "3dobjsp_pc": Format("data/**/3dobjsp.pc", "three_d_objsp_pc.hexpat", True),
    }

    SEPARATOR: str = ","

    @dataclass
    class Args:
        fror_research: pathlib.Path
        fror: pathlib.Path
        verbose: bool
        imhex: pathlib.Path
        formats: str

    @classmethod
    def setup(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("fror_research", type=pathlib.Path)
        parser.add_argument("fror", type=pathlib.Path)
        parser.add_argument("--verbose", action=argparse.BooleanOptionalAction)
        parser.add_argument("--imhex", type=pathlib.Path, default="imhex")
        parser.add_argument(
            "--formats",
            type=str,
            default=ImHexValidateSubcommand.SEPARATOR.join(
                ImHexValidateSubcommand.FORMATS.keys()
            ),
        )

    @classmethod
    def execute(cls, args: Args) -> None:
        includes = args.fror_research / "includes"
        patterns = args.fror_research / "patterns"
        formats = args.formats.split(ImHexValidateSubcommand.SEPARATOR)
        for format_name, format in ImHexValidateSubcommand.FORMATS.items():
            if format_name not in formats:
                continue
            if args.verbose:
                print(f"Processing format: {format_name}")
            for input in args.fror.glob(format.glob):
                if args.verbose:
                    print(f"Processing input: {input}")
                decompressed_input = input
                tmp_ctx = (
                    tempfile.TemporaryDirectory()
                    if format.compressed
                    else contextlib.nullcontext()
                )
                with tmp_ctx as tmp:
                    if format.compressed:
                        tmp_str = typing.cast(str, tmp)
                        with open(input, "rb") as f:
                            decompressed_binary_reader = get_decompressed_binary_reader(
                                f
                            )
                            decompressed_data = decompressed_binary_reader.read()
                            decompressed_input = (
                                pathlib.Path(tmp_str) / "decompressed.bin"
                            )
                            decompressed_input.write_bytes(decompressed_data)

                    completed_process = subprocess.run(
                        [
                            args.imhex,
                            "--pl",
                            "run",
                            "--includes",
                            includes,
                            "--pattern",
                            patterns / format.pattern,
                            "--input",
                            decompressed_input,
                        ],
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
                        print(error)


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

    args = parser.parse_args()
    args.klass.pre_execute(args)


if __name__ == "__main__":
    main()
