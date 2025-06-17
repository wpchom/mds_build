#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess

sys.dont_write_bytecode = True

from build import error


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"


def _download_by_curl(url, path, proxy):
    if path == None:
        cmd_curl = ["curl", "-L", url, "-O"]
    else:
        cmd_curl = ["curl", "-L", url, "-o", path]

    cmd_curl += ["-A", USER_AGENT]
    if proxy != None:
        cmd_curl += ["--proxy", proxy]

    ret = subprocess.run(cmd_curl + ["--parallel"], check=False)
    if ret.returncode == 2:
        ret = subprocess.run(cmd_curl, check=False)

    return ret.returncode


def _download_by_wget(url, path, proxy):
    if path == None:
        cmd_wget = ["wget", url]
    else:
        cmd_wget = ["wget", url, "-O", path]

    cmd_wget += ["-U", USER_AGENT]
    if proxy != None:
        cmd_wget += ["--proxy", proxy]

    ret = subprocess.run(cmd_wget, check=False)
    if ret.returncode != 0:
        os.remove(path)

    return ret.returncode


def download_pkg(url, path, proxy):
    if os.path.exists(path):
        return
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    path_tmp = path + ".tmp"

    try:
        ret = _download_by_curl(url, path_tmp, proxy)
    except KeyboardInterrupt:
        try:
            os.remove(path_tmp)
        except:
            pass
        raise (KeyboardInterrupt)

    if ret != 0:
        print(f"download `{path}` from `{url}` failed")
        exit(-1)

    os.rename(path_tmp, path)


def download_git(url, branch, path, proxy):
    if (not os.path.exists(path)) or (not ".git" in os.listdir(path)):
        try:
            os.makedirs(path, exist_ok=True)
            git_command = ["git", "clone", url, path, "--depth=1", "--recursive"]
            if branch != None:
                git_command += ["-b", branch]
            if proxy != None:
                git_command += [
                    "-c",
                    f"http.proxy={proxy}",
                    "-c",
                    f"https.proxy={proxy}",
                ]

            ret = subprocess.run(git_command, check=False)
            if ret.returncode != 0:
                error(f"git clone `{url}` failed")

        except KeyboardInterrupt:
            try:
                shutil.rmtree(path)
            except:
                pass
            raise (KeyboardInterrupt)

    else:
        try:
            ret = subprocess.run(["git", "status"], cwd=path)
            if (
                "Changes not staged for commit" in ret
                or "Changes to be committed" in ret
            ):
                error(f"git repository `{path}` has uncommitted changes")

            ret = subprocess.run(["git", "fetch", "--all"], cwd=path)
            if ret.returncode != 0:
                error(f"git fetch `{path}` failed")

            ret = subprocess.run(["git", "checkout", branch], cwd=path)
            if ret.returncode != 0:
                error(f"git checkout `{branch}` failed")

        except Exception:
            error(f"git `{url}` branch `{branch}` fetch failed, remove it to retry")
