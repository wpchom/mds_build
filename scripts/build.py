#!/usr/bin/python3

import os
import time
import shutil
import argparse
import platform
import subprocess

MDS_BUILD_DIR = os.path.join(
    os.path.realpath(os.path.dirname(os.path.realpath(__file__))), "../")
MDS_CACHE_DIR = os.path.join(MDS_BUILD_DIR, "cache")


def error(message):
    print("\033[31m>>> {}\033[0m".format(message), flush=True)
    exit(-1)


def unzip(filepath, decompress_dir):
    import zipfile
    zip = zipfile.ZipFile(filepath)
    zip.extractall(decompress_dir)
    zip.close()


def download_by_curl(path, url, proxy):
    try:
        cmd_curl = ["curl", "-C", "-", "--parallel", "-L", url, "-o", path]
        if (proxy != None):
            cmd_curl += ["--proxy", proxy]

        subprocess.run(cmd_curl)
        return 0
    except:
        return -1


def download_by_wget(path, url, proxy):
    try:
        cmd_wget = ["wget", "-c", url, "-O", path]
        if (proxy != None):
            cmd_wget += ["--proxy", proxy]

        subprocess.run(cmd_wget)
        return 0
    except:
        return -1


def download_by_libcurl(path, url, proxy):
    import pycurl

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.FOLLOWLOCATION, True)
    c.setopt(c.RESUME_FROM, 0)

    if proxy:
        c.setopt(c.PROXY, proxy)

    with open(path, 'wb') as f:
        c.setopt(c.WRITEDATA, f)
        try:
            c.perform()
            ret = 0
        except:
            ret = -1
    c.close()

    return ret


def download_by_requests(path, url, proxy):
    import requests

    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy
        }
    else:
        proxies = {}

    try:
        r = requests.get(url, stream=True, proxies=proxies)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return 0
    except:
        return -1


def download_by_urllib(path, url, proxy):
    import urllib.request

    if proxy:
        handler = urllib.request.ProxyHandler({
            'http': proxy,
            'https': proxy
        })
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)

    try:
        urllib.request.urlretrieve(url, path)
        return 0
    except:
        return -1


def download(path, url, proxy):
    path_tmp = path+".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)


    if download_by_curl(path_tmp, url, proxy) == 0:
            pass
    elif download_by_wget(path_tmp, url, proxy) == 0:
            pass
    elif download_by_libcurl(path_tmp, url, proxy) == 0:
            pass
    elif download_by_requests(path_tmp, url, proxy) == 0:
            pass
    elif download_by_urllib(path_tmp, url, proxy) == 0:
            pass
    else:
        error("download '{}' from '{}' fail".format(path, url))

    os.rename(path_tmp, path)


def check_git():
    git_bin = shutil.which("git")

    ret = subprocess.run([git_bin, "--version"], stdout=subprocess.DEVNULL)
    if ret.returncode != 0:
        error("'git' command is erorr")

    return (git_bin)


def check_gn(proxy):
    gn_bin = shutil.which("gn")

    try:
        subprocess.run([gn_bin, "--version"], stdout=subprocess.DEVNULL)
        return (gn_bin)
    except:
        pass

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys
    plat_sys = "win" if plat_sys == "windows" else plat_sys

    plat_mach = platform.uname().machine.lower()
    plat_mach = "arm64" if plat_mach == "aarch64" else plat_mach

    gn_bin = os.path.join(MDS_CACHE_DIR, "bin",
                          "gn-{}-{}/gn".format(plat_sys, plat_mach))
    if not os.path.exists(gn_bin):
        gn_download_url = "https://chrome-infra-packages.appspot.com/dl/gn/gn/{}-{}/+/latest".format(
            plat_sys, plat_mach)

        gn_download_path = os.path.dirname(gn_bin) + ".zip"
        if not os.path.exists(gn_download_path):
            download(gn_download_path, gn_download_url, proxy)
        unzip(gn_download_path, os.path.dirname(gn_bin))
        os.chmod(gn_bin, 0o755)

    try:
        subprocess.run([gn_bin, "--version"], stdout=subprocess.DEVNULL)
        return (gn_bin)
    except:
        error("'{}' error, please remove it to retry".format(gn_bin))


def check_ninja(proxy):
    ninja_bin = shutil.which("ninja")

    try:
        subprocess.run([ninja_bin, "--version"], stdout=subprocess.DEVNULL)
        return (ninja_bin)
    except:
        pass

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys

    ninja_bin = os.path.join(MDS_CACHE_DIR, "bin",
                             "ninja-{}/ninja".format(plat_sys))
    if not os.path.exists(ninja_bin):
        ninja_download_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-{}.zip".format(
            plat_sys)

        ninja_download_path = os.path.dirname(ninja_bin) + ".zip"
        if not os.path.exists(ninja_download_path):
            download(ninja_download_path, ninja_download_url, proxy)
        unzip(ninja_download_path, os.path.dirname(ninja_bin))
        os.chmod(ninja_bin, 0o755)

    try:
        subprocess.run([ninja_bin, "--version"], stdout=subprocess.DEVNULL)
        return (ninja_bin)
    except:
        error("'{}' error, please remove it to retry".format(ninja_bin))


def build_argparse():
    parser = argparse.ArgumentParser(
        description="build.py [target] [-b buildir] [-f dotfile] [-o outdir] [-v] [-r] [-k] [-x proxy]")

    parser.add_argument("target", type=str, nargs="*",
                        help="build target for gn")
    parser.add_argument("-b", "--buildir", type=str, default=None,
                        help="build root directory for gn")
    parser.add_argument("-f", "--dotfile", type=str, default=None,
                        help="build dotfile for gn")
    parser.add_argument("-o", "--outdir", type=str, default=None,
                        help="build out directory for gn")

    parser.add_argument("-k", "--update", action="store_true", default=False,
                        help="update mds_build from git")
    parser.add_argument("-r", "--rebuild", action="store_true", default=False,
                        help="clean outdir before build")
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="show build verbose output")
    parser.add_argument("-x", "--proxy", type=str, default=os.getenv("MDS_BUILD_PROXY"),
                        help="proxy server, default getenv MDS_BUILD_PROXY")

    parser.add_argument("--args", type=str, action="append", default=[],
                        help="gn gen with args")

    args = parser.parse_args()

    if args.proxy != None:
        os.environ['MDS_BUILD_PROXY'] = args.proxy

    if args.buildir != None:
        args.buildir = os.path.abspath(args.buildir)
    else:
        args.buildir = os.path.abspath(os.getcwd())

    if args.dotfile != None:
        args.dotfile = os.path.abspath(args.dotfile)
    else:
        args.dotfile = os.path.join(os.getcwd(), ".gn")

    if args.outdir != None:
        args.outdir = os.path.abspath(args.outdir)
    else:
        args.outdir = os.path.join(os.getcwd(), "outdir")

    return (args)


class Build:
    def debug(self, message):
        if (self.args.verbose):
            print(message, flush=True)

    def __init__(self):
        self.args = build_argparse()
        self.debug(self.args)

        self.git = check_git()
        self.gn = check_gn(self.args.proxy)
        self.ninja = check_ninja(self.args.proxy)

    def update(self):
        if not ".git" in os.listdir(MDS_BUILD_DIR):
            error("mds_build is not a git repository")

        try:
            subprocess.run([self.git, "pull"], cwd=MDS_BUILD_DIR)
        except:
            error("mds_build git pull error")

        if os.path.exists(os.path.join(self.args.outdir, "build.pkgs")):
            os.remove(os.path.join(self.args.outdir, "build.pkgs"))

    def clean(self):
        print("\033[33m>>> Build clean output directory '{}'\033[0m".format(
              self.args.outdir), flush=True)

        if os.path.exists(self.args.outdir):
            subprocess.run([self.ninja, "-t", "clean"], cwd=self.args.outdir)

    def build(self):
        stime = time.perf_counter()
        print("\033[32m>>> Building action start '{}' with '{}'\033[0m".format(
            self.args.buildir, self.args.dotfile), flush=True)

        cmd_gn_build = ['gen', self.args.outdir, '--export-compile-commands']
        cmd_gn_build += ['--root=%s' % self.args.buildir]
        cmd_gn_build += ['--dotfile=%s' % self.args.dotfile]

        cmd_gn_build += ['--args=%s' %
                         ' '.join(['mds_build_dir=\"%s\"' % MDS_BUILD_DIR] + self.args.args)]

        self.debug(' '.join([self.gn] + cmd_gn_build))

        res = subprocess.run([self.gn] + cmd_gn_build, cwd=self.args.buildir)
        if res.returncode:
            error(res)
        with open(os.path.join(self.args.outdir, ".gitignore"), "w+") as f:
            f.write("*.*\n")
            f.close()

        cmd_ninja_build = [self.ninja, "-C", self.args.outdir]
        cmd_ninja_build += ['-v'] if self.args.verbose else []
        self.debug(" ".join(cmd_ninja_build))
        res = subprocess.run(cmd_ninja_build, cwd=self.args.outdir)

        etime = time.perf_counter()

        if (res.returncode == 0):
            print("\033[32m>>> Building action finished cost time: %.3fs\033[0m\n" %
                  float(etime - stime), flush=True)
        else:
            print("\033[31m>>> Building action error cost time: %.3fs\033[0m\n" %
                  float(etime - stime), flush=True)
            error(res)


def main():
    build = Build()

    if build.args.update:
        build.update()

    if build.args.rebuild:
        build.clean()

    build.build()


if '__main__' == __name__:
    main()
