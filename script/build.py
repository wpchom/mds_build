#!/usr/bin/python3

import os
import time
import shutil
import argparse
import platform
import subprocess

MDS_BUILD_BINDIR = os.path.join(os.path.dirname(__file__), "..", "bin")


def error(message):
    print("\033[31m>>> {}\033[0m".format(message), flush=True)
    exit(-1)


def debug(verbose, *contexts):
    if (verbose):
        print(*contexts, flush=True)


def unzip(filepath, decompress_dir):
    import zipfile
    zip = zipfile.ZipFile(filepath)
    zip.extractall(decompress_dir)
    zip.close()


def download(path, url, args):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)

        command = ["curl", "--parallel", "-L", url, "-o", path+".tmp"]
        if (args.proxy != None):
            command += ["--proxy", args.proxy]

        debug(args.verbose, " ".join(command))

        if subprocess.run(" ".join(command)).returncode != 0:
            exit(-1)

        os.rename(path+".tmp", path)
    except:
        error("download '{}' from '{}' fail".format(path, url))


def check_git():
    git_cmd = shutil.which("git")

    ret = subprocess.run([git_cmd, "--version"], stdout=subprocess.DEVNULL)
    if ret.returncode != 0:
        error("'git' command is erorr")

    return (git_cmd)


def check_gn(args):
    gn_cmd = shutil.which("gn")

    try:
        subprocess.run([gn_cmd, "--version"], stdout=subprocess.DEVNULL)
        return (gn_cmd)
    except:
        pass

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys
    plat_sys = "win" if plat_sys == "windows" else plat_sys

    plat_mach = platform.uname().machine.lower()
    plat_mach = "arm64" if plat_mach == "aarch64" else plat_mach

    gn_cmd = os.path.join(
        MDS_BUILD_BINDIR, "gn-{}-{}/gn".format(plat_sys, plat_mach))
    if not os.path.exists(gn_cmd):
        gn_download_url = "https://chrome-infra-packages.appspot.com/dl/gn/gn/{}-{}/+/latest".format(
            plat_sys, plat_mach)

        gn_download_path = os.path.dirname(gn_cmd) + ".zip"
        if not os.path.exists(gn_download_path):
            download(gn_download_path, gn_download_url, args)
        unzip(gn_download_path, os.path.dirname(gn_cmd))
        os.chmod(gn_cmd, 0o755)

    try:
        subprocess.run([gn_cmd, "--version"], stdout=subprocess.DEVNULL)
        return (gn_cmd)
    except:
        error("'{}' error, please remove it to retry".format(gn_cmd))


def check_ninja(args):
    ninja_cmd = shutil.which("ninja")

    try:
        subprocess.run([ninja_cmd, "--version"], stdout=subprocess.DEVNULL)
        return (ninja_cmd)
    except:
        pass

    plat_sys = platform.uname().system.lower()
    plat_sys = "mac" if plat_sys == "darwin" else plat_sys

    ninja_cmd = os.path.join(
        MDS_BUILD_BINDIR, "ninja-{}/ninja".format(plat_sys))
    if not os.path.exists(ninja_cmd):
        ninja_download_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-{}.zip".format(
            plat_sys)

        ninja_download_path = os.path.dirname(ninja_cmd) + ".zip"
        if not os.path.exists(ninja_download_path):
            download(ninja_download_path, ninja_download_url, args)
        unzip(ninja_download_path, os.path.dirname(ninja_cmd))
        os.chmod(ninja_cmd, 0o755)

    try:
        subprocess.run([ninja_cmd, "--version"], stdout=subprocess.DEVNULL)
        return (ninja_cmd)
    except:
        error("'{}' error, please remove it to retry".format(ninja_cmd))


def build_argparse():
    parser = argparse.ArgumentParser(
        description="build.py [-b buildir] [-f dotfile] [-o outdit] [-v]")

    parser.add_argument("-b", "--buildir", type=str, default=None,
                        help="gn root directory")
    parser.add_argument("-f", "--dotfile", type=str, default=None,
                        help="gn build dotfile")
    parser.add_argument("-o", "--outdir", type=str, default=None,
                        help="gn output directory")

    parser.add_argument("-x", "--proxy", type=str, default=None,
                        help="proxy server, default: None")
    parser.add_argument("-r", "--rebuild", dest="rebuild",
                        action="store_true", default=False,
                        help="clean outdir before build")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", default=False,
                        help="show build verbose output")

    parser.add_argument("--args", type=str, default=None,
                        help="gn gen with args")

    args = parser.parse_args()

    if args.buildir.startswith(".."):
        error("don use parent dir to bildir")

    if args.buildir != None:
        args.buildir = os.path.join(os.getcwd(), args.buildir)
    args.buildir = os.path.relpath(args.buildir, os.getcwd())

    if args.outdir == None:
        args.outdir = os.path.join(os.path.realpath(
            os.getcwd()), "outdir", os.path.split(args.buildir)[-1])

    if args.proxy != None:
        os.environ['MDS_PROXY'] = args.proxy

    return (args)


class Build:
    def __init__(self, args):
        self.args = args
        debug(args.verbose, args)

    def clean(self, outdir):
        print("\033[33m>>> Build clean output directory '{}'\033[0m".format(
              self.args.outdir), flush=True)

        git_ignore = os.path.join(outdir, ".gitignore")
        if os.path.exists(git_ignore) and open(git_ignore, "r").read() == "/*\n":
            shutil.rmtree(outdir)

    def build(self):
        dotfile = os.path.join(
            self.args.buildir, "dotfile", self.args.dotfile + '.gn')
        outdir = os.path.join(self.args.outdir, self.args.dotfile)

        if not os.path.exists(dotfile):
            error("'{}' is not exists".format(dotfile))

        if self.args.rebuild:
            self.clean(outdir)

        stime = time.time()
        print("\033[32m>>> Building action start '{}' with '{}'\033[0m".format(
            self.args.buildir, self.args.dotfile), flush=True)

        try:
            os.makedirs(outdir, exist_ok=True)
            open(os.path.join(outdir, ".gitignore"), "w+").write("/*\n")
        except:
            error("some error on '{}'".format(self.args.outdir))

        gn_gen_cmd = [self.gn, "gen", outdir,
                      "--root="+self.args.buildir, "--dotfile="+dotfile]
        if self.args.args != None:
            gn_gen_cmd += ["--args={}".format(self.args.args)]
        debug(self.args.verbose, " ".join(gn_gen_cmd))

        try:
            ret = subprocess.run(" ".join(gn_gen_cmd), shell=True)
            if ret.returncode != 0:
                error("gn gen error:%d", ret.returncode)
        except:
            if os.path.exists(outdir):
                shutil.rmtree(outdir)
            error("gn gen error on '{}'".format(outdir))

        ninja_build_cmd = [self.ninja, "-C", outdir,
                           ('-v' if self.args.verbose else '')]
        debug(self.args.verbose, " ".join(ninja_build_cmd))

        ret = subprocess.run(" " .join(ninja_build_cmd), shell=True)
        etime = time.time()
        if (ret.returncode == 0):
            print("\033[32m>>> Building action finished cost time: %.3fms\033[0m\n" %
                  float(etime - stime), flush=True)
        else:
            print("\033[31m>>> Building action error cost time: %.3fms\033[0m\n" %
                  float(etime - stime), flush=True)

        return (ret.returncode)


def build_action(args):
    build = Build(args)

    # check
    build.git = check_git()
    build.gn = check_gn(args)
    build.ninja = check_ninja(args)

    ret = 0

    if build.args.dotfile == None:
        dotfiles = os.listdir(os.path.join(args.buildir, "dotfile"))
        for d in dotfiles:
            if not d.endswith(".gn"):
                continue
            if d != ".gn":
                build.args.dotfile = d[:-3]
                ret = build.build()
                if ret != 0:
                    break

    else:
        ret = build.build()

    return (ret)


def main():
    build_action(build_argparse())


if '__main__' == __name__:
    main()
