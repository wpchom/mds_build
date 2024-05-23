#!/usr/bin/python3

import os
import time
import shutil
import argparse
import platform
import subprocess

BINDIR = os.path.join(os.path.dirname(__file__), ".bin")


def error(message):
    print("\033[31m>>> {}\033[0m".format(message), flush=True)
    exit(-1)


def unzip(filepath, decompress_dir):
    import zipfile
    zip = zipfile.ZipFile(filepath)
    zip.extractall(decompress_dir)
    zip.close()


def build_argparse():
    parser = argparse.ArgumentParser(
        description="build.py [build|rebuild|clean] [-b buildir] [-f dotfile] [-o outdit] [-v]")

    parser.add_argument("action", type=str,
                        metavar="action to build(b) / clean(c) / rebuild(r)",
                        choices=["build", "b", "clean", "c", "rebuild", "r"],
                        default="build", nargs='?')

    parser.add_argument("-b", "--buildir", type=str, default=None,
                        help="gn root directory, default: ./")
    parser.add_argument("-f", "--dotfile", type=str, default=None,
                        help="gn dotfile, default: <buildir>/.gn")
    parser.add_argument("-o", "--outdir", type=str, default=None,
                        help="gn output directory, default: ./outdir")

    parser.add_argument("-x", "--proxy", type=str, default=None,
                        help="proxy server, default: None")
    parser.add_argument("-r", "--rebuild", dest="verbose",
                        action="store_true", default=False,
                        help="show build verbose output")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", default=False,
                        help="show build verbose output")

    args = parser.parse_args()

    if args.buildir.startswith(".."):
        error("don use parent dir to bildir")

    if args.buildir != None:
        args.buildir = os.path.join(os.getcwd(), args.buildir)
    args.buildir = os.path.relpath(args.buildir, os.getcwd())

    if args.outdir == None:
        args.outdir = os.path.join(os.path.realpath(
            os.getcwd()), "outdir", os.path.split(args.buildir)[-1])

    if args.dotfile == None:
        args.dotfile = os.path.join(args.buildir, ".gn")
    else:
        args.outdir = os.path.join(args.outdir, args.dotfile)
        args.dotfile = os.path.join(
            args.buildir, "dotfile", args.dotfile+".gn")

    if args.proxy != None:
        os.environ['MDS_PROXY'] = args.proxy

    return (args)


class Build:
    def __init__(self, args):
        self.args = args
        self.verbose(self.args)

    def error(self, message):
        print("\033[31m>>> {}\033[0m".format(message), flush=True)
        exit(-1)

    def verbose(self, *contexts):
        if (self.args.verbose):
            print(*contexts, flush=True)

    def download(self, path, url):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            command = ["curl", "--parallel", "-L", url, "-o", path+".tmp"]

            if (self.args.proxy != None):
                command += ["--proxy", self.args.proxy]

            self.verbose("{}", command)
            if subprocess.run(command).returncode != 0:
                exit(-1)

            os.rename(path+".tmp", path)
        except:
            error("download '{}' from '{}' fail".format(path, url))

    def clean(self):
        print("\033[33m>>> Build clean output directory '{}'\033[0m".format(
              self.args.outdir), flush=True)

        git_ignore = os.path.join(self.args.outdir, ".gitignore")
        if os.path.exists(git_ignore) and open(git_ignore, "r").read() == "/*\n":
            shutil.rmtree(self.args.outdir)

    def build(self):
        if not os.path.exists(self.args.dotfile):
            error("'{}' is not exists".format(self.args.dotfile))

        stime = time.time()
        print("\033[32m>>> Building action start '{}' with '{}'\033[0m".format(
            self.args.buildir, self.args.dotfile), flush=True)

        try:
            os.makedirs(self.args.outdir, exist_ok=True)
            open(os.path.join(self.args.outdir, ".gitignore"), "w+").write("/*\n")
        except:
            error("some error on '{}'".format(self.args.outdir))

        gn_gen_cmd = " ".join([self.gn, "gen", self.args.outdir,
                              "--root="+self.args.buildir, "--dotfile="+self.args.dotfile])
        self.verbose(gn_gen_cmd)

        try:
            ret = subprocess.run(gn_gen_cmd, shell=True)
            if ret.returncode != 0:
                error("gn gen error:%d", ret.returncode)
        except:
            if os.path.exists(self.args.outdir):
                shutil.rmtree(self.args.outdir)
            error("gn gen error on '{}'".format(self.args.outdir))

        ninja_build_cmd = " ".join(
            [self.ninja, "-C", self.args.outdir, ('-v' if self.args.verbose else '')])
        self.verbose(ninja_build_cmd)

        ret = subprocess.run(ninja_build_cmd, shell=True)
        etime = time.time()
        if (ret.returncode == 0):
            print("\033[32m>>> Building action finished cost time: %.3fms\033[0m" %
                  float(etime - stime), flush=True)
        else:
            print("\033[31m>>> Building action error cost time: %.3fms\033[0m" %
                  float(etime - stime), flush=True)

        return (ret.check_returncode)

    def check_git(self):
        git_cmd = shutil.which("git")

        ret = subprocess.run([git_cmd, "--version"], stdout=subprocess.DEVNULL)
        if ret.returncode != 0:
            error("'git' command is erorr")

        self.git = git_cmd

    def check_gn(self):
        gn_cmd = shutil.which("gn")

        try:
            subprocess.run([gn_cmd, "--version"], stdout=subprocess.DEVNULL)
            self.gn = gn_cmd
            return
        except:
            pass

        plat_sys = platform.uname().system.lower()
        plat_sys = "mac" if plat_sys == "darwin" else plat_sys
        plat_sys = "win" if plat_sys == "windows" else plat_sys

        plat_mach = platform.uname().machine.lower()
        plat_mach = "arm64" if plat_mach == "aarch64" else plat_mach

        gn_cmd = os.path.join(
            BINDIR, "gn-{}-{}/gn".format(plat_sys, plat_mach))
        if not os.path.exists(gn_cmd):
            gn_download_url = "https://chrome-infra-packages.appspot.com/dl/gn/gn/{}-{}/+/latest".format(
                plat_sys, plat_mach)

            gn_download_path = os.path.dirname(gn_cmd) + ".zip"
            if not os.path.exists(gn_download_path):
                self.download(gn_download_path, gn_download_url)
            unzip(gn_download_path, os.path.dirname(gn_cmd))
            os.chmod(gn_cmd, 0o755)

        try:
            subprocess.run([gn_cmd, "--version"], stdout=subprocess.DEVNULL)
            self.gn = gn_cmd
            return
        except:
            error("'{}' error, please remove it to retry".format(gn_cmd))

    def check_ninja(self):
        ninja_cmd = shutil.which("ninja")

        try:
            subprocess.run([ninja_cmd, "--version"], stdout=subprocess.DEVNULL)
            self.ninja = ninja_cmd
            return
        except:
            pass

        plat_sys = platform.uname().system.lower()
        plat_sys = "mac" if plat_sys == "darwin" else plat_sys

        ninja_cmd = os.path.join(BINDIR, "ninja-{}/ninja".format(plat_sys))
        if not os.path.exists(ninja_cmd):
            ninja_download_url = "https://github.com/ninja-build/ninja/releases/latest/download/ninja-{}.zip".format(
                plat_sys)

            ninja_download_path = os.path.dirname(ninja_cmd) + ".zip"
            if not os.path.exists(ninja_download_path):
                self.download(ninja_download_path, ninja_download_url)
            unzip(ninja_download_path, os.path.dirname(ninja_cmd))
            os.chmod(ninja_cmd, 0o755)

        try:
            subprocess.run([ninja_cmd, "--version"], stdout=subprocess.DEVNULL)
            self.ninja = ninja_cmd
            return
        except:
            error("'{}' error, please remove it to retry".format(ninja_cmd))


def main():
    build = Build(build_argparse())

    # check
    build.check_git()
    build.check_gn()
    build.check_ninja()

    if build.args.action == "c" or build.args.action == "check":
        return

    if build.args.action == "r" or build.args.action == "rebuild":
        build.clean()

    return (build.build())


if '__main__' == __name__:
    main()
