#!/usr/bin/python3

import os
import re
import sys
import json
import shutil
import argparse
import datetime
import subprocess
import urllib.request

PACKAGE_UPDATE_DIFF_TIMESTAMP = (48*60*60)


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
        command = " ".join(
            [shutil.which('7z'), "x", filepath, "-o" + decompress_dir])
        if subprocess.run(command, shell=True, capture_output=True).returncode != 0:
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


def repos_get_ver(api, match):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
    }
    request = urllib.request.Request(api, headers=headers)
    with urllib.request.urlopen(request) as response:
        if response.status == 200:  # HTTP 200 OK
            kv_json = json.loads(response.read().decode())
        else:
            error("failed to fetch latest release")

    if match.startswith("-r:"):
        latest_kv = kv_json[-1]
        match = match[3:]
    else:
        latest_kv = kv_json[0]

    key, val = match.split(":")

    m = re.match(val, latest_kv[key])
    if m:
        return m.group(1)
    else:
        error("no match key '{}' value '{}'".format(key, latest_kv[key]))


class Package:
    def __init__(self, args):
        self.args = args

        if self.args.ver == "latest":
            if self.args.api == None:
                self.args.api = "get from api"
            self.checklatest()

        self.args.url = self.args.url.replace("{version}", self.args.ver)

    def checklatest(self):
        diff_time = -1
        latest_file = os.path.join(
            self.args.package, self.args.name, ".latest")
        if os.path.exists(latest_file):
            f = open(latest_file, mode="r", encoding="utf-8")
            kv = json.loads(f.read())
            if (('name' in kv and kv['name'] == self.args.name) and
                ('version' in kv and kv['version'] != None) and
                    ('timestamp' in kv and kv['timestamp'] != None)):
                dt = datetime.datetime.now(datetime.timezone.utc)
                utc_time = dt.replace(tzinfo=datetime.timezone.utc)
                diff_time = utc_time.timestamp() - kv['timestamp']
            f.close()

        if diff_time < 0 or diff_time > PACKAGE_UPDATE_DIFF_TIMESTAMP:
            self.args.ver = repos_get_ver(self.args.api, self.args.match)

            os.makedirs(os.path.dirname(latest_file), exist_ok=True)
            with open(latest_file, mode="w+", encoding="utf-8") as f:
                dt = datetime.datetime.now(datetime.timezone.utc)
                utc_time = dt.replace(tzinfo=datetime.timezone.utc)
                kv = {'name': self.args.name, 'version': self.args.ver,
                      'timestamp': int(utc_time.timestamp())}
                f.write(json.dumps(kv, indent=4))
                f.close()

        else:
            self.args.ver = kv['version']

    def download_pkg(self, package_dir):
        pkg_suffix = ""

        for suffix in [".zip", ".7z", ".rar", ".tar.gz", ".tar.bz2", ".tar.xz"]:
            if self.args.url.endswith(suffix):
                pkg_suffix = suffix
                break

        if pkg_suffix == "":
            error("pacakge '{}' file suffix is not support".format(self.args.name))

        download_name = "{}-{}{}".format(os.path.basename(self.args.name),
                                         self.args.ver, pkg_suffix)
        download_path = os.path.join(
            self.args.download, self.args.name, download_name)
        if not os.path.exists(download_path):
            try:
                os.makedirs(os.path.dirname(download_path), exist_ok=True)
                command = " ".join(
                    ["curl", "--parallel", "-L", self.args.url, "-o", download_path+".tmp"])
                if os.environ.get("MDS_PROXY") != None:
                    command += ["-x", os.environ.get("MDS_PROXY"), command]
                if subprocess.run(command, shell=True, capture_output=True).returncode != 0:
                    error("package '{}' download failed".format(self.args.name))
                    return

                os.rename(download_path+".tmp", download_path)
            except:
                error("package '{}' download failed command:'{}'".format(
                    self.args.name, command))

        if pkg_suffix == ".zip":
            unzip(download_path, package_dir)
        elif pkg_suffix == ".7z":
            unarchive(download_path, package_dir)
        elif pkg_suffix == ".rar":
            unrar(download_path, package_dir)
        else:
            untar(download_path, package_dir)

    def downloaod_git(self, package_dir):
        git_package_dir = os.path.join(
            package_dir, "{}-{}".format(os.path.basename(self.args.name), self.args.ver))
        git_download_dir = os.path.join(
            self.args.download, self.args.name, "{}-{}".format(self.args.name, self.args.ver))

        if (not os.path.exists(git_download_dir)) or (not ".git" in os.listdir(git_download_dir)):
            try:
                os.makedirs(git_download_dir, exist_ok=True)
                command = " ".join(["git", "clone", "--depth=1", "--recursive",
                                    "--branch="+self.args.ver, self.args.url, git_download_dir])
                if subprocess.run(command, shell=True, capture_output=True).returncode != 0:
                    error("git clone '{}' fail".format(self.args.url))
                os.makedirs(git_package_dir, exist_ok=True)
                os.rename(git_download_dir, git_package_dir)
            except:
                error("package '{}' git clone failed".format(self.args.name))
        else:
            try:
                os.chdir(git_download_dir)
                if subprocess.run(" ".join(["git", "fetch", "--all", "--depth=1"]), shell=True, capture_output=True).returncode != 0:
                    error("git fetch '{}' fail".format(self.args.name))
                if subprocess.run(" ".join(["git", "checkout", self.args.ver]), shell=True, capture_output=True).returncode != 0:
                    error("git checkout '{}' fail".format(self.args.name))
                os.makedirs(git_package_dir, exist_ok=True)
                os.rename(git_download_dir, git_package_dir)
            except:
                error("package '{}' git fetch failed, remove it to retry".format(
                    self.args.name))

    def download(self):
        package_dir = os.path.join(
            self.args.package, self.args.name, self.args.ver)

        if os.path.exists(package_dir):
            f = open(os.path.join(package_dir, ".pkg"),
                     mode="r", encoding="utf-8")
            kv = json.loads(f.read())
            if (('name' in kv and kv['name'] == self.args.name) and
                ('version' in kv and kv['version'] == self.args.ver) and
                    ('timestamp' in kv and kv['timestamp'] != None)):
                return
            else:
                try:
                    os.removedirs(package_dir)
                except:
                    error("package dir '{}' is not of '{}' remove it to retry".format(
                        package_dir, self.args.name))

        if self.args.url.endswith(".git"):
            self.downloaod_git(package_dir)
        else:
            self.download_pkg(package_dir)
            pass

        with open(os.path.join(package_dir, ".pkg"), mode="w+", encoding="utf-8") as f:
            dt = datetime.datetime.now(datetime.timezone.utc)
            utc_time = dt.replace(tzinfo=datetime.timezone.utc)
            kv = {'name': self.args.name, 'version': self.args.ver,
                  'timestamp': int(utc_time.timestamp())}
            f.write(json.dumps(kv))
            f.close()


def main():
    parser = argparse.ArgumentParser(
        description="package.py <url> [-k <key>] [-m <match>]")

    parser.add_argument("name", type=str, nargs='?', const=1, default=None,
                        help="name of package")
    parser.add_argument("-u", "--url", type=str, required=True,
                        help="package download url")
    parser.add_argument("-v", "--ver", type=str, required=True,
                        help="package download version")
    parser.add_argument("-a", "--api", type=str, default=None,
                        help="api of package to get latest version")
    parser.add_argument("-m", "--match", type=str, default="name:v(.*)",
                        help="match re string of value")
    parser.add_argument("-d", "--download", type=str, default=None,
                        help="root dir of package download")
    parser.add_argument("-p", "--package", type=str, default=None,
                        help="root dir of package installed")
    parser.add_argument("-x", "--proxy", type=str, default=None,
                        help="proxy of package download")

    args = parser.parse_args()

    if args.name == None:
        error("package name is not defined")

    if (args.download == None) or (args.package == None):
        error("invaild args of download or package")

    package = Package(args)
    package.download()

    sys.stdout.write(str(package.args.ver))


if __name__ == '__main__':
    main()
