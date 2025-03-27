#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil

sys.dont_write_bytecode = True

from build import error


def _add_argument(parser):
    parser.add_argument("input", help="file to compress or decompress")

    parser.add_argument("-o", "--output", help="output for compress or decompress")

    parser.add_argument(
        "-d",
        "--decompress",
        action="store_true",
        default=False,
        help="decompress action",
    )

    parser.add_argument(
        "-f", "--format", type=str, default="lzma", help="format for compress"
    )
    parser.add_argument("--args", type=str, default="", help="args for compress")

    parser.add_argument("-y", "--force", action="store_true", default=False)


def parser(subparsers):
    parser = subparsers.add_parser("compress", help="compress or decompress")

    parser.add_argument("-v", "--verbose", action="store_true", default=False)

    _add_argument(parser)


def action(args):
    if args.decompress:
        decompress(args.input, args.output, args.force)
    else:
        encompress(args.input, args.output, args.format, args.args, args.force)


def _decompress_tar(input_file, output_dir):
    import tarfile

    with tarfile.open(input_file) as f:
        f.extractall(output_dir)
        f.close()


def _decompress_zip(input_file, output_dir):
    import zipfile

    with zipfile.ZipFile(input_file) as f:
        f.extractall(output_dir)
        f.close()


def _decompress_archive(input_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    p7z = shutil.which("7z")
    if p7z != None:
        import subprocess

        p7z_command = [p7z, "x", input_file, "-o", output_dir]
        ret = subprocess.run(p7z_command, cwd=output_dir, check=False)
        if ret.returncode != 0:
            error("7z decompress failed")

    else:
        try:
            import libarchive

            with libarchive.file_reader(input_file) as archive:
                for entry in archive:
                    target_path = os.path.join(output_dir, entry.pathname)

                    if entry.isdir:
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, "wb") as f:
                            for block in entry.get_blocks():
                                f.write(block)

        except ImportError:
            try:
                import py7zr

                py7z = py7zr.SevenZipFile(input_file, "r")
                py7z.extractall(output_dir)
                py7z.close()

            except ImportError:
                error("please install `7z` or python module `libarchive`/`py7zr`")


def _decompress_rar(input_file, output_dir):
    try:
        import rarfile

        with rarfile.RarFile(input_file) as f:
            f.extractall(output_dir)

    except ImportError:
        _decompress_archive(input_file, output_dir)


def decompress(input_file, output_dir, force):
    if output_dir == None:
        output_dir = os.path.dirname(input_file)

    if os.path.exists(output_dir):
        if force:
            shutil.rmtree(output_dir)
        else:
            error("output directory already exists:", output_dir)

    try:
        if input_file.endswith(".zip"):
            _decompress_zip(input_file, output_dir)
        elif input_file.endswith(".rar"):
            _decompress_rar(input_file, output_dir)
        elif ".tar." in input_file:
            _decompress_tar(input_file, output_dir)
        else:
            _decompress_archive(input_file, output_dir)
    except Exception as e:
        error(f"decompress `{input_file}` failed:\n{e}")


def _string_to_dict(string):
    str_dict = {}

    try:
        for s in string.split(","):
            if "=" in s:
                key, value = s.split("=")
                str_dict[key] = value if value.startswith("'") else int(value)
    except Exception as e:
        error(f"parse `{string}` failed:\n{e}")

    return str_dict


def _encompress_lzma(input_path, output_file, args, force):
    import lzma
    import tarfile

    filter = args

    filter["id"] = lzma.FILTER_LZMA1
    if not "dict_size" in filter:
        filter["dict_size"] = 4096
    if not "lc" in filter:
        filter["lc"] = 1
    if not "lp" in filter:
        filter["lp"] = 1
    if not "pb" in filter:
        filter["pb"] = 1
    if not "nice_len" in filter:
        filter["nice_len"] = 273
    if not "depth" in filter:
        filter["depth"] = 0

    try:
        compressor = lzma.LZMACompressor(lzma.FORMAT_ALONE, filters=[filter])
    except Exception as e:
        error(f"compressor error: {e}")

    if os.path.isfile(input_path):
        if output_file is None:
            output_file = os.path.realpath(input_path) + ".lzma"
    else:
        if output_file is None:
            output_file = os.path.realpath(input_path) + ".tar.lzma"

    if os.path.exists(output_file):
        if force:
            os.remove(output_file)
        else:
            error("output file already exists:", output_file)

    if os.path.isfile(input_path):
        with open(input_path, "rb") as f:
            with open(output_file, "wb") as fout:
                fout.write(compressor.compress(f.read()))
                fout.write(compressor.flush())
    else:
        try:
            with tarfile.open(output_file + ".tmp", "w") as tar:
                tar.add(input_path, arcname=os.path.basename(input_path))
                tar.close()

            with open(output_file + ".tmp", "rb") as f:
                with open(output_file, "wb") as fout:
                    fout.write(compressor.compress(f.read()))
                    fout.write(compressor.flush())

            os.remove(output_file + ".tmp")

        except KeyboardInterrupt:
            os.remove(output_file + ".tmp")
            raise (KeyboardInterrupt)


def _encompress_xz(input_path, output_file, args, force):
    import lzma
    import tarfile

    filter = args

    filter["id"] = lzma.FILTER_LZMA2

    try:
        compressor = lzma.LZMACompressor(lzma.FORMAT_XZ, filters=[filter])
    except Exception as e:
        error(f"compressor error: {e}")

    if os.path.isfile(input_path):
        if output_file is None:
            output_file = os.path.realpath(input_path) + ".xz"
    else:
        if output_file is None:
            output_file = os.path.realpath(input_path) + ".tar.xz"

    if os.path.exists(output_file):
        if force:
            os.remove(output_file)
        else:
            error("output file already exists:", output_file)

    if os.path.isfile(input_path):
        with open(input_path, "rb") as f:
            with open(output_file, "wb") as fout:
                fout.write(compressor.compress(f.read()))
                fout.write(compressor.flush())
    else:
        with tarfile.open(output_file, "w:xz") as tar:
            tar.add(input_path, arcname=os.path.basename(input_path))
            tar.close()


def encompress(input_path, output_file, format, args, force):
    if not os.path.exists(input_path):
        error(f"input file `{input_path}` not exists")

    args_dict = _string_to_dict(args)

    if format == "lzma":
        _encompress_lzma(input_path, output_file, args_dict, force)
    elif format == "xz":
        _encompress_xz(input_path, output_file, args_dict, force)
    else:
        error(f"unsupported format {format}")


def main():
    pass


if __name__ == "__main__":
    main()
