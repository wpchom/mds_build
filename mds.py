#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import argparse

sys.dont_write_bytecode = True

MDS_BUILD_GIT = "https://github.com/wpchom/mds_build.git"

MDS_BUILD_DIR = os.getenv("MDS_BUILD_DIR") or os.path.join(
    os.path.expanduser("~"), ".mds_build"
)


def error(*args):
    message = " ".join(str(arg) for arg in args)
    print(f"\n\033[31m>>> [mds] {message}\033[0m", flush=True)
    exit(-1)


def mds_check(update):
    if not ".git" in os.listdir(MDS_BUILD_DIR):
        error(f"`{MDS_BUILD_DIR}` is not a git repository")

    if not os.path.exists(MDS_BUILD_DIR):
        try:
            subprocess.run(["git", "clone", MDS_BUILD_GIT, MDS_BUILD_DIR])
        except Exception as e:
            error(f"`git clone {MDS_BUILD_GIT} {MDS_BUILD_DIR}` failed", f"\n{str(e)}")
    elif update:
        try:
            subprocess.run(["git", "-C", MDS_BUILD_DIR, "pull"])
        except Exception as e:
            error(f"`git -C {MDS_BUILD_DIR} pull` failed", f"\n{str(e)}")


def mds_parser():
    try:
        sys.path.append(os.path.join(MDS_BUILD_DIR, "scripts", "mds"))
        import build, clean, package, compress, upkgbin,logparse

    except ImportError:
        error(f"mds import failed, plase check `{MDS_BUILD_DIR}`")

    parser = argparse.ArgumentParser(description="MDS build tool")
    subparsers = parser.add_subparsers(title="action", dest="action")

    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("-k", "--update", action="store_true", default=False)
    parser.add_argument(
        "-x",
        "--proxy",
        default=os.getenv("MDS_BUILD_PROXY"),
        help="proxy server, default getenv MDS_BUILD_PROXY",
    )

    build.parser(subparsers)
    clean.parser(subparsers)
    package.parser(subparsers)
    compress.parser(subparsers)
    upkgbin.parser(subparsers)
    logparse.parser(subparsers)

    parser.set_defaults(action="build")

    return parser


def mds_action(args):
    try:
        sys.path.append(os.path.join(MDS_BUILD_DIR, "scripts", "mds"))
        import build, clean, package, compress, upkgbin, logparse

    except ImportError:
        error(f"mds import failed, plase check `{MDS_BUILD_DIR}`")

    args.mds_build_dir = MDS_BUILD_DIR
    args.mds_cache_dir = os.getenv("MDS_CACHE_DIR") or os.path.join(
        MDS_BUILD_DIR, "cache"
    )

    if (args.action == "build") or (args.action == "b"):
        build.action(args)
    elif (args.action == "clean") or (args.action == "c"):
        clean.action(args)
    elif (args.action == "package") or (args.action == "p"):
        package.action(args)
    elif (args.action == "compress") or (args.action == "e"):
        compress.action(args)
    elif (args.action == "upkgbin") or (args.action == "u"):
        upkgbin.action(args)
    elif (args.action == "logparse") or (args.action == "g"):
        logparse.action(args)
    else:
        error(f"unknown action `{args.action}`")


def main():
    mds_check(False)

    args = mds_parser().parse_args()

    if args.verbose:
        print(f"{args}")

    if args.proxy != None:
        os.environ["MDS_BUILD_PROXY"] = args.proxy

    mds_check(args.update)
    mds_action(args)

    if os.getenv("MDS_BUILD_PROXY"):
        os.environ["MDS_BUILD_PROXY"] = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error("KeyboardInterrupt")
