#!/usr/bin/python3

import os
import time
import shutil
import argparse
import platform
import subprocess

BINDIR = os.path.join(os.path.dirname(__file__), ".pkgs/bin")


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
        description="build.py <buildir> [-f dotfile] [-o outdit] [-v] [-r]")

    parser.add_argument("buildir", type=str, nargs="?",
                        help="buildir for project where gn build root dir")
    parser.add_argument("-f", "--dotfile", type=str, default=None,
                        help="default all dotfile in project")
    parser.add_argument("-o", "--outdir", type=str, default=None,
                        help="gn output directory, default: ./out")

    parser.add_argument("-x", "--proxy", type=str, default=None,
                        help="proxy server, default: None")
    parser.add_argument("-r", "--rebuild", dest="rebuild",
                        action="store_true", default=False,
                        help="show build verbose output")
    parser.add_argument("-v", "--verbose", dest="verbose",
                        action="store_true", default=False,
                        help="show build verbose output")

    args = parser.parse_args()

    return (args)


class Build:
    def __init__(self, args):
        self.args = args
        self.verbose(self.args)

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

            os.rename(path + ".tmp", path)
        except:
            error("download '{}' from '{}' fail".format(path, url))

    def build(self, dotname):
        # dotfile
        dotfile = os.path.abspath(os.path.join(
            self.args.buildir, "dotfile", dotname + ".gn"))
        if not os.path.exists(dotfile):
            error("dotfiel '{}' is not exist".format(dotfile))

        # outdir
        if self.args.outdir == None:
            self.args.outdir = os.path.join(os.getcwd(), "out")
        outdir = os.path.join(self.args.outdir, os.path.split(
            os.path.abspath(self.args.buildir))[-1], dotname)

        # start time
        stime = time.time()

        # rebuild
        if self.args.rebuild:
            print("\033[33m>>> Build clean output directory '{}'\033[0m".format(
                outdir), flush=True)
            git_ignore = os.path.join(outdir, ".gitignore")
            if os.path.exists(git_ignore) and open(git_ignore, "r").read() == "/*\n":
                shutil.rmtree(outdir)

        print("\033[32m>>> Building with '{}'\033[0m".format(
            dotfile), flush=True)

        # create outdir
        try:
            os.makedirs(outdir, exist_ok=True)
            open(os.path.join(outdir, ".gitignore"), "w+").write("/*\n")
        except:
            error("some error on '{}'".format(outdir))

        # gn gen
        gn_gen_cmd = " ".join(
            [self.gn, "gen", outdir, "--root="+self.args.buildir, "--dotfile="+dotfile])
        self.verbose(gn_gen_cmd)

        try:
            ret = subprocess.run(gn_gen_cmd, shell=True)
            if ret.returncode != 0:
                error("gn gen error:%d", ret.returncode)
        except:
            if os.path.exists(outdir):
                shutil.rmtree(outdir)
            error("gn gen error on '{}'".format(outdir))

        # ninja build
        ninja_build_cmd = " ".join(
            [self.ninja, "-C", outdir, ('-v' if self.args.verbose else '')])
        self.verbose(ninja_build_cmd)

        ret = subprocess.run(ninja_build_cmd, shell=True)
        etime = time.time()
        if (ret.returncode == 0):
            print("\033[32m>>> Building finished cost time: %.3fms\033[0m" %
                  float(etime - stime), flush=True)
        else:
            print("\033[31m>>> Building error cost time: %.3fms\033[0m" %
                  float(etime - stime), flush=True)

        # build finish
        print("\n")

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

    # proxy
    if build.args.proxy != None:
        os.environ['MDS_PROXY'] = build.args.proxy

    # check
    build.check_git()
    build.check_gn()
    build.check_ninja()

    if build.args.buildir == None:
        error("no input buildir")
    elif not os.path.exists(os.path.join(build.args.buildir, "BUILD.gn")):
        error("no BUILD.gn in '{}'".format(build.args.buildir))

    if build.args.dotfile == None:
        if not os.path.exists(os.path.join(build.args.buildir, "dotfile")):
            error("no dotfile dir in '{}'".format(build.args.buildir))
        for d in os.listdir(os.path.join(build.args.buildir, "dotfile")):
            if d.endswith('.gn'):
                build.build(d[:-3])
    else:
        build.build(build.args.dotfile)


if '__main__' == __name__:
    main()
