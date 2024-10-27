#!/usr/bin/python3

import os
import sys
import json
import shutil
import argparse
import subprocess


MDS_BUILD_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def pkg_repos_dir(args):
    repos_path = os.path.join(MDS_BUILD_DIR, "repos", args.name[0], args.name)

    return (repos_path)


def pkg_download_dir(args):
    download_path = os.path.join(
        MDS_BUILD_DIR, "pkgs", "download", args.name[0], args.name)
    download_fext = args.url.split(".")[-1]

    if args.url.split(".")[-2] == "tar":
        download_fext = "tar." + download_fext

    return (download_path, download_fext)


def pkg_resource_dir(args):
    resource_dir = os.path.join(MDS_BUILD_DIR, "pkgs",
                                "resource", args.name[0], args.name, "{}-{}".format(args.name, args.ver))

    return (resource_dir)


def error(message):
    print(message, flush=True)
    exit(-1)


def untar(filepath, decompress_dir):
    import tarfile
    tar = tarfile.open(filepath)
    tar.extractall(decompress_dir)
    tar.close()


def unzip(filepath, decompress_dir):
    import zipfile
    zip = zipfile.ZipFile(filepath)
    zip.extractall(decompress_dir)
    zip.close()


def unarchive(filepath, decompress_dir):
    if not os.path.exists(decompress_dir):
        os.makedirs(decompress_dir)
    os.chdir(decompress_dir)

    if shutil.which('7z') != None:
        cmd_7z = [shutil.which('7z'), "x", filepath, "-o" + decompress_dir]
        if subprocess.run(cmd_7z).returncode != 0:
            error("7z decompress '{}' to '{}' failed".format(
                filepath, decompress_dir))
    else:
        try:
            import libarchive
            libarchive.extract_file(filepath)
        except ModuleNotFoundError:
            try:
                import py7zr
                py7z = py7zr.SevenZipFile(filepath, 'r')
                py7z.extractall(decompress_dir)
                py7z.close()
            except ModuleNotFoundError:
                error(
                    "please install python module 'libarchive'/'py7zr', or '7z' in PATH")


def unrar(filepath, decompress_dir):
    try:
        import rarfile
        rar = rarfile.RarFile(filepath)
        rar.extractall(decompress_dir)
        rar.close()
    except ImportError:
        unarchive(filepath, decompress_dir)


def pkg_download(args, download_path, download_fext):
    def pkg_download_git(args, download_path, resource_path):
        if (not os.path.exists(resource_path)) or (not ".git" in os.listdir(resource_path)):
            git_download_path = os.path.join(
                download_path, "{}-{}".format(args.name, args.ver))
            try:
                os.makedirs(download_path, exist_ok=True)
                cmd_git = ["git", "clone", "--depth=1", "--recursive",
                           "--branch="+args.ver, args.url, git_download_path]
                if subprocess.run(cmd_git, cwd=download_path).returncode != 0:
                    error("git clone '{}' fail".format(args.url))
                os.makedirs(resource_path, exist_ok=True)
                os.rename(git_download_path, resource_path)
            except:
                error("package '{}' git clone failed".format(args.name))
        else:
            try:
                if subprocess.run(["git", "fetch", "--depth=1", "--all"], cwd=resource_path).returncode != 0:
                    error("git fetch '{}' fail".format(args.name))
                if subprocess.run(["git", "checkout", args.ver], cwd=resource_path).returncode != 0:
                    error("git checkout '{}' fail".format(args.name))
            except:
                error("package '{}' git fetch failed, remove it to retry".format(
                    args.name))

    def pkg_download_pack(args, download_path, download_fext):
        download_file = os.path.join(
            download_path, "{}-{}.{}".format(args.name, args.ver, download_fext))

        if not os.path.exists(download_file):
            try:
                os.makedirs(download_path, exist_ok=True)
                cmd_curl = ["curl", "--parallel", "-L",
                            args.url, "-o", download_file+".tmp"]
                if args.proxy != None:
                    cmd_curl += ["-x", args.proxy]

                res = subprocess.run(cmd_curl, cwd=download_path)
                if res.returncode != 0:
                    print(" ".join(cmd_curl))
                    error("curl download '{}' fail".format(args.url))

                os.rename(download_file+".tmp", download_file)
            except:
                error("package '{}' download failed".format(args.name))

        return (download_file)

    def pkg_download_unpack(download_fext, download_file, resource_path):
        if os.path.exists(resource_path):
            return

        if download_fext == "zip":
            unzip(download_file, resource_path)
        elif download_fext == "7z":
            unarchive(download_file, resource_path)
        elif download_fext == "rar":
            unrar(download_file, resource_path)
        else:
            untar(download_file, resource_path)

    resource_path = pkg_resource_dir(args)
    if not os.path.exists(resource_path):
        if args.url.endswith(".git"):
            pkg_download_git(args, download_path, resource_path)
        else:
            download_file = pkg_download_pack(
                args, download_path, download_fext)
            pkg_download_unpack(download_fext, download_file, resource_path)

    return (resource_path)


def version_from_api(args):
    import re
    import urllib.request

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
    }
    request_api = urllib.request.Request(args.api, headers=headers)

    if args.proxy != None:
        proxy = urllib.request.ProxyHandler(
            {"http": args.proxy, "https": args.proxy})
        opener = urllib.request.build_opener(proxy)
    else:
        opener = urllib.request.build_opener()

    with opener.open(request_api) as response:
        if response.status == 200:  # HTTP 200 OK
            kv_json = json.loads(response.read().decode())
        else:
            error("failed to fetch latest release")

    if args.match.startswith("-r:"):
        latest_kv = kv_json[-1]
        match = match[3:]
    else:
        latest_kv = kv_json[0]
        match = args.match

    key, val = match.split(":")

    m = re.match(val, latest_kv[key])
    if m:
        return m.group(1)
    else:
        error("no match key '{}' value '{}'".format(key, latest_kv[key]))


def pkg_build_version(args):
    import fcntl

    # gn gen out dir & ninja build dir
    verfile = os.path.join(os.getcwd(), "build.pkgs")

    if not os.path.exists(verfile):
        with open(verfile, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            verjson = {}
            verjson[args.name] = args.ver if (
                args.ver != 'latest') else version_from_api(args)
            json.dump(verjson, f, indent=4)
    else:
        with open(verfile, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            verjson = json.load(f)
            if not args.name in verjson:
                verjson[args.name] = args.ver if (
                    args.ver != 'latest') else version_from_api(args)
                f.seek(0)
                json.dump(verjson, f, indent=4)

    return (verjson[args.name])


def main():
    parser = argparse.ArgumentParser(
        description="package.py <name> -v <version> [-u <url>]")

    parser.add_argument("name", type=str,
                        help="name of package")
    parser.add_argument("-v", "--ver", type=str, default=None,
                        help="package download version")
    parser.add_argument("-u", "--url", type=str, default=None,
                        help="package download url")
    parser.add_argument("-a", "--api", type=str, default=None,
                        help="package get version from api")
    parser.add_argument("-m", "--match", type=str, default="",
                        help="package match version from api")
    parser.add_argument("-p", "--path", type=str, default="./",
                        help="package path join in resouce dir")

    parser.add_argument("-x", "--proxy", type=str, default=os.getenv("MDS_BUILD_PROXY"),
                        help="proxy of package download")

    args = parser.parse_args()

    if args.ver == None and args.url == None:
        resource_path = pkg_repos_dir(args)
        if not os.path.exists(resource_path):
            error("package '{}' not found".format(args.name))
        else:
            sys.stdout.write(resource_path)
        return

    if args.ver == None:
        error("package '{}' version is not defined".format(args.name))
    if args.url == None:
        error("package '{}' url is not defined".format(args.name))
    elif args.ver == 'latest' and args.api == None:
        error("package '{}' api is not defined".format(args.name))
    else:
        args.ver = pkg_build_version(args)

    args.url = args.url.replace("{version}", args.ver)

    (download_path, download_fext) = pkg_download_dir(args)

    resource_path = pkg_download(args, download_path, download_fext)

    sys.stdout.write(os.path.join(
        resource_path, args.path.replace("{version}", args.ver)))


if __name__ == '__main__':
    main()
