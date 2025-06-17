#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse

sys.dont_write_bytecode = True

from build import error, debug


def _add_argument(parser):
    parser.add_argument("name", type=str, nargs="?", help="name of package")
    parser.add_argument(
        "-r", "--ver", type=str, default=None, help="package download version"
    )
    parser.add_argument(
        "-u", "--url", type=str, default=None, help="package download url"
    )
    parser.add_argument(
        "-a", "--api", type=str, default=None, help="package get version from api"
    )
    parser.add_argument(
        "-m", "--match", type=str, default="", help="package match version from api"
    )
    parser.add_argument(
        "-p", "--path", type=str, default="./", help="package path join in resource dir"
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        default=False,
        help="list package in resource dir",
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        default=False,
        help="skip generate build.pkgs file",
    )
    parser.add_argument(
        "-x",
        "--proxy",
        default=os.getenv("MDS_BUILD_PROXY"),
        help="proxy server, default getenv MDS_BUILD_PROXY",
    )


def parser(subparsers):
    parser = subparsers.add_parser("package", aliases=["p"], help="package fetch")

    _add_argument(parser)


def _pkg_package_path(args):
    package_path = os.path.join(args.mds_build_dir, "packages", args.name[0], args.name)

    return package_path


def _pkg_download_path(args):
    download_path = os.path.join(
        args.mds_cache_dir, "download", args.name[0], args.name
    )

    return download_path


def _pkg_resource_path(args):
    resource_path = os.path.join(
        args.mds_cache_dir,
        "resource",
        args.name[0],
        args.name,
        "{}-{}".format(args.name, args.ver),
    )

    return resource_path


def _version_from_api(args):
    import re
    import urllib.request

    import download

    headers = {"User-Agent": download.USER_AGENT}
    request_api = urllib.request.Request(args.api, headers=headers)

    if args.proxy != None:
        proxy = urllib.request.ProxyHandler({"http": args.proxy, "https": args.proxy})
        opener = urllib.request.build_opener(proxy)
    else:
        opener = urllib.request.build_opener()

    try:
        with opener.open(request_api) as response:
            if response.status == 200:  # HTTP 200 OK
                kv_json = json.loads(response.read().decode())
            else:
                error("failed to fetch latest release")
    except urllib.error.URLError as e:
        error(f"Failed to send request: {e}")

    if args.match.startswith("-r:"):
        latest_kv = kv_json[-1]
        match = args.match[3:]
    else:
        latest_kv = kv_json[0]
        match = args.match

    key, val = match.split(":")

    m = re.match(val, latest_kv[key])
    if m:
        return m.group(1)
    else:
        error(f"no match key `{key}` value `{latest_kv[key]}`")


def _pkg_build_version(args):
    import fcntl

    if args.skip:
        return args.ver if (args.ver != "latest") else _version_from_api(args)

    # gn gen out dir & ninja build dir
    verfile = os.path.join(os.getcwd(), "build.pkgs")

    if not os.path.exists(verfile):
        with open(verfile, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            verjson = {}
            verjson[args.name] = (
                args.ver if (args.ver != "latest") else _version_from_api(args)
            )
            json.dump(verjson, f, indent=4)
    else:
        with open(verfile, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            verjson = json.load(f)
            if not args.name in verjson:
                verjson[args.name] = (
                    args.ver if (args.ver != "latest") else _version_from_api(args)
                )
                f.seek(0)
                json.dump(verjson, f, indent=4)

    return verjson[args.name]


def _pkg_list(args):
    pkgs = {}

    if args.name == None:
        debug(f"{'Package'}")
        debug("-" * 24)
        for d in os.listdir(os.path.join(args.mds_build_dir, "packages")):
            for f in os.listdir(os.path.join(args.mds_build_dir, "packages", d)):
                debug(f)
    elif os.path.exists(os.path.join(os.getcwd(), args.name, "build.pkgs")):
        with open(os.path.join(os.getcwd(), args.name, "build.pkgs"), "r") as f:
            pkgs = json.load(f)

        package_len = max([len(p) for p in pkgs.keys()], default=8)
        version_len = max([len(str(v)) for v in pkgs.values()], default=8)
        debug(f"{'Package':<{package_len}}    {'Version':<{version_len}}")
        debug("-" * (package_len + version_len + 12))
        for p, v in pkgs.items():
            debug(f"{p:<{package_len}}    {v:<{version_len}}")


def action(args):
    import download

    if args.list:
        _pkg_list(args)
        return

    if (args.ver == None) and (args.url == None):
        package_path = _pkg_package_path(args)
        if not os.path.exists(package_path):
            error(f"package `{args.name}` not found")
        else:
            sys.stdout.write(os.path.abspath(package_path))
        return

    if args.ver == None:
        error(f"package `{args.name}` version is not defined")
    if args.url == None:
        error(f"package `{args.name}` url is not defined")
    elif args.ver == "latest" and args.api == None:
        error(f"package `{args.name}` api is not defined")
    else:
        args.ver = _pkg_build_version(args)

    args.url = args.url.replace("{version}", args.ver)

    resource_path = _pkg_resource_path(args)
    if not os.path.exists(resource_path):
        download_path = _pkg_download_path(args)
        if args.url.endswith(".git"):
            download.download_git(args.url, args.ver, download_path, args.proxy)
            os.makedirs(resource_path, exist_ok=True)
            os.rename(download_path, resource_path)
        else:
            import compress

            if args.url.split(".")[-2] == "tar":
                download_file = f"{args.name}-{args.ver}.tar.{args.url.split('.')[-1]}"
            else:
                download_file = f"{args.name}-{args.ver}.{args.url.split('.')[-1]}"

            download.download_pkg(
                args.url, os.path.join(download_path, download_file), args.proxy
            )
            compress.decompress(
                os.path.join(download_path, download_file), resource_path, False
            )
    else:
        # not update with package
        pass

    sys.stdout.write(
        os.path.abspath(
            os.path.join(resource_path, args.path.replace("{version}", args.ver))
        )
    )


def main():
    parser = argparse.ArgumentParser()
    _add_argument(parser)

    args = parser.parse_args()

    args.mds_build_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    )

    args.mds_cache_dir = os.getenv("MDS_CACHE_DIR") or os.path.join(
        args.mds_build_dir, "cache"
    )

    action(args)


if __name__ == "__main__":
    main()
