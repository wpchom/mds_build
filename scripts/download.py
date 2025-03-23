#!/usr/bin/python3

import os
import argparse
import subprocess


def download_by_curl(path, url, proxy):
    try:
        cmd_curl = ["curl", "-C", "-", "--parallel", "-L", url, "-o", path]
        if (proxy != None):
            cmd_curl += ["--proxy", proxy]

        subprocess.run(cmd_curl)
        return 0
    except Exception:
        return -1


def download_by_wget(path, url, proxy):
    try:
        cmd_wget = ["wget", "-c", url, "-O", path]
        if (proxy != None):
            cmd_wget += ["--proxy", proxy]

        subprocess.run(cmd_wget)
        return 0
    except Exception:
        return -1


def download_by_libcurl(path, url, proxy):
    try:
        import pycurl

        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.FOLLOWLOCATION, True)
        c.setopt(c.RESUME_FROM, 0)

        if proxy:
            c.setopt(c.PROXY, proxy)

        with open(path, 'wb') as f:
            c.setopt(c.WRITEDATA, f)
            c.perform()
            c.close()

        return 0
    except Exception:
        return -1


def download_by_requests(path, url, proxy):
    try:
        import requests

        proxies = {} if proxy is None else {'http': proxy, 'https': proxy}

        r = requests.get(url, stream=True, proxies=proxies)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        return 0
    except Exception:
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
    except Exception:
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


def main():
    parser = argparse.ArgumentParser(description="download package")

    parser.add_argument("url", help="download url")
    parser.add_argument("path", help="download path")
    parser.add_argument("--proxy", help="proxy server")

    args = parser.parse_args()

    download(args.path, args.url, args.proxy)


if __name__ == "__main__":
    main()
