#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import subprocess

sys.dont_write_bytecode = True


def error(*args):
    message = " ".join(str(arg) for arg in args)
    sys.stderr.write(f"\033[31m>>> {message}\033[0m\n")
    sys.stderr.flush()
    exit(-1)


def debug(*args):
    message = " ".join(str(arg) for arg in args)
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


def parser(subparsers):
    parser = subparsers.add_parser("build", aliases=["b"], help="build project")

    parser.add_argument("target", nargs="?", default="default", help="target to build")
    parser.add_argument(
        "-b", "--buildir", default=None, help="build root directory for gn"
    )
    parser.add_argument("-d", "--dotfile", default=None, help="build dotfile for gn")
    parser.add_argument(
        "-o", "--outdir", default=None, help="build output directory for gn"
    )

    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument(
        "-r",
        "--rebuild",
        action="store_true",
        default=False,
        help="clean outdir before build",
    )
    parser.add_argument(
        "-x",
        "--proxy",
        default=os.getenv("MDS_BUILD_PROXY"),
        help="proxy server, default getenv MDS_BUILD_PROXY",
    )

    parser.add_argument("--args", action="append", default=[], help="gn gen with args")


def action(args):
    if ("buildir" in args) and (args.buildir != None):
        args.buildir = os.path.abspath(args.buildir)
    else:
        args.buildir = os.path.abspath(os.getcwd())

    if ("dotfile" in args) and (args.dotfile != None):
        args.dotfile = os.path.abspath(args.dotfile)
    else:
        args.dotfile = os.path.join(os.getcwd(), ".gn")

    if ("outdir" in args) and (args.outdir != None):
        args.outdir = os.path.abspath(args.outdir)
    else:
        args.outdir = os.path.join(os.getcwd(), "outdir")

    if not "args" in args:
        args.args = []

    if ("rebuild" in args) and args.rebuild:
        import clean

        clean.action(args)

    _build(args)


def check_git():
    git_bin = shutil.which("git")
    if git_bin == None:
        error("'git' command is not found")

    return git_bin


def check_gn(mds_cache_dir, proxy):
    gn_bin = shutil.which("gn")

    if gn_bin != None:
        ret = subprocess.run(
            [gn_bin, "--version"], stdout=subprocess.DEVNULL, check=False
        )
        if ret.returncode == 0:
            return gn_bin

    import platform

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys
    plat_sys = "win" if plat_sys == "windows" else plat_sys

    plat_mach = platform.uname().machine.lower()
    plat_mach = "arm64" if plat_mach == "aarch64" else plat_mach

    gn_bin = os.path.join(mds_cache_dir, "bin", f"gn-{plat_sys}-{plat_mach}/gn")
    if not os.path.exists(gn_bin):
        gn_download_url = f"https://chrome-infra-packages.appspot.com/dl/gn/gn/{plat_sys}-{plat_mach}/+/latest"
        gn_download_path = os.path.dirname(gn_bin) + ".zip"

        if not os.path.exists(gn_download_path):
            import download

            download.download_pkg(gn_download_url, gn_download_path, proxy)

        import compress

        compress.decompress(gn_download_path, os.path.dirname(gn_bin))

        os.chmod(gn_bin, 0o755)

    try:
        ret = subprocess.run([gn_bin, "--version"], stdout=subprocess.DEVNULL)
    except Exception:
        error(f"`{gn_bin}` error, please remove it to retry")

    return gn_bin


def check_ninja(mds_cache_dir, proxy):
    ninja_bin = shutil.which("ninja")

    if ninja_bin != None:
        ret = subprocess.run(
            [ninja_bin, "--version"], stdout=subprocess.DEVNULL, check=False
        )
        if ret.returncode == 0:
            return ninja_bin

    import platform

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys

    ninja_bin = os.path.join(mds_cache_dir, "bin", f"ninja-{plat_sys}/ninja")
    if not os.path.exists(ninja_bin):
        ninja_download_url = f"https://github.com/ninja-build/ninja/releases/latest/download/ninja-{plat_sys}.zip"
        ninja_download_path = os.path.dirname(ninja_bin) + ".zip"

        if not os.path.exists(ninja_download_path):
            import download

            download.download_pkg(ninja_download_url, ninja_download_path, proxy)

        import compress

        compress.decompress(ninja_download_path, os.path.dirname(ninja_bin))

        os.chmod(ninja_bin, 0o755)

    try:
        ret = subprocess.run([ninja_bin, "--version"], stdout=subprocess.DEVNULL)
    except Exception:
        error(f"`{ninja_bin}` error, please remove it to retry")

    return ninja_bin


def _build(args):
    stime = time.perf_counter()
    print(
        f"\033[32m>>> Building action start `{args.buildir}` with `{args.dotfile}`\033[0m",
        flush=True,
    )

    # gn gen
    gn_bin = check_gn(args.mds_cache_dir, args.proxy)
    gn_command = [gn_bin, "gen", args.outdir, "--export-compile-commands"]
    gn_command += ["--root=%s" % args.buildir, "--dotfile=%s" % args.dotfile]

    gn_command += [
        "--args=%s" % " ".join(['mds_build_dir="%s"' % args.mds_build_dir] + args.args)
    ]

    if args.verbose:
        debug(" ".join(gn_command))

    ret = subprocess.run(gn_command, cwd=args.buildir, check=False)
    if ret.returncode != 0:
        error(f"`{' '.join(gn_command)}` error")

    # git ignore
    with open(os.path.join(args.outdir, ".gitignore"), "w+") as f:
        f.write("*.*/\n")

    # ninja build
    ninja_bin = check_ninja(args.mds_cache_dir, args.proxy)
    ninja_command = [ninja_bin, "-C", args.outdir]

    if args.verbose:
        ninja_command += ["-v"]
        debug(" ".join(ninja_command))

    ret = subprocess.run(ninja_command, cwd=args.outdir, check=False)

    # complete
    etime = time.perf_counter()
    if ret.returncode == 0:
        print(
            "\033[32m>>> Building action finished cost time: %.3fs\033[0m\n"
            % float(etime - stime),
            flush=True,
        )
    else:
        print(
            "\033[31m>>> Building action error cost time: %.3fs\033[0m\n"
            % float(etime - stime),
            flush=True,
        )
        error(ret)
