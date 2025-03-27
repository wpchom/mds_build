#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess

sys.dont_write_bytecode = True


def parser(subparsers):
    parser = subparsers.add_parser("clean", aliases=["c"], help="clean build")

    parser.add_argument("outdir", help="output dir to clean")

    parser.add_argument("-v", "--verbose", action="store_true", default=False)


def action(args):
    from build import debug, check_ninja

    if (not os.path.exists(args.outdir)) or (
        not "build.ninja" in os.listdir(args.outdir)
    ):
        debug(f"`{args.outdir}` is not a build out dir")
        return

    ninja_bin = check_ninja(args.mds_cache_dir, args.proxy)

    print(
        f"\033[33m>>> Build clean output directory `{args.outdir}`\033[0m", flush=True
    )

    ninja_cmd = [ninja_bin, "-C", args.outdir, "-t", "clean"]

    if args.verbose:
        debug(" ".join(ninja_cmd))

    subprocess.run(ninja_cmd, check=True)
