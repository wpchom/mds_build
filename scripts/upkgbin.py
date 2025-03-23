#!/usr/bin/python3

import os
import argparse
import hashlib
import struct


'''
#ifndef MDS_BOOT_UPGRADE_MAGIC
#define MDS_BOOT_UPGRADE_MAGIC 0xBDAC9ADE
#endif

typedef struct MDS_BOOT_BinInfo {
    uint8_t check[sizeof(uint16_t)];
    uint8_t flag[sizeof(uint16_t)];
    uint8_t dstAddr[sizeof(uint32_t)];
    uint8_t srcSize[sizeof(uint32_t)];
    uint8_t hash[MDS_BOOT_CHKHASH_SIZE];

    // context of `uint8_t data[srcSize]` for upgrade bin
} MDS_BOOT_BinInfo_t;

typedef struct MDS_BOOT_UpgradeInfo {
    uint8_t check[sizeof(uint16_t)];  // check upgradeInfo header
    uint8_t magic[sizeof(uint32_t)];  // magic for firmware check
    uint8_t count[sizeof(uint16_t)];  // count of binInfos
    uint8_t size[sizeof(uint32_t)];   // totalSize
    uint8_t hash[MDS_BOOT_CHKHASH_SIZE];

    // context of `MDS_BOOT_BinInfo_t binInfo[count]` for upgrade bin combain
} MDS_BOOT_UpgradeInfo_t;
'''


def crc16(data):
    crc = 0

    for d in data:
        crc ^= d
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1

    return crc & 0xFFFF


def error(message):
    print("\033[31m[Error]\033[0m {}".format(message), flush=True)
    exit(-1)


class BinFile:
    def __init__(self, path, addr, flag):
        if not os.path.exists(path):
            error(f"file {path} not exist")

        if flag < 0 or flag > 0xFFFF:
            error(f"flag {flag} out of range")

        self.path = path
        self.flag = flag
        self.addr = addr
        self.size = os.path.getsize(path)
        with open(path, 'rb') as f:
            self.hash = hashlib.sha256(f.read()).digest()

        self.header = struct.pack('>H', self.flag) + \
            struct.pack('>II', self.addr, self.size) + self.hash
        self.check = crc16(self.header)
        self.header = struct.pack('>H', int(self.check)) + self.header


def upkgbin(args):
    bin_count = 0
    total_size = 0
    upgrade_hash = hashlib.sha256()
    bin_list = []
    for bin in args.bin:
        bin_count += 1

        if (len(bin.split(',')) < 3):
            error(f"bin parameter '{bin}' format incorrect")

        path = os.path.abspath(bin.split(',')[0])
        addr = int(bin.split(',')[1], 16)
        flag = int(bin.split(',')[2], 16)
        b = BinFile(path, addr, flag)

        total_size += b.size + len(b.header)
        upgrade_hash.update(b.header)
        with open(path, 'rb') as f:
            upgrade_hash.update(f.read())
        bin_list.append(b)

    upgrade_header = struct.pack('>IH', args.magic, bin_count) + \
        struct.pack('>I', total_size) + upgrade_hash.digest()
    upgrade_check = crc16(upgrade_header)
    upgrade_header = struct.pack('>H', int(upgrade_check)) + upgrade_header

    upkg_output = args.output
    print(f'[upkgbin] count:{bin_count} into:{upkg_output}')

    os.makedirs(os.path.dirname(upkg_output), exist_ok=True)
    with open(upkg_output, 'wb') as f:
        f.write(upgrade_header)
        for i, b in enumerate(bin_list):
            f.write(b.header)
            with open(b.path, 'rb') as bin_file:
                f.write(bin_file.read())
            print(f'''- bin {i+1}: {b.path}, addr:{hex(b.addr)}, flag:{
                  hex(b.flag)}, size:{b.size}''')

    upkg_filesz = os.path.getsize(upkg_output)
    limit_rate = (upkg_filesz / args.limit) * 100 if args.limit > 0 else 0

    if args.limit > 0 and upkg_filesz > args.limit:
        error(f"[upkgbin] upkg:{upkg_filesz} limit:{args.limit} rate:{limit_rate:.2f}%")
    else:
        print(f"[upkgbin] upkg:{upkg_filesz} limit:{args.limit} rate:{limit_rate:.2f}%")


def type_val(x):
    try:
        value = int(x, 16)
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError()
        else:
            return int(x, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{x}' not a uint16 hex integer")


def type_hex(x):
    try:
        if x.endswith('k') or x.endswith('K'):
            return int(x[:-1], 10) * 1024
        elif x.endswith('m') or x.endswith('M'):
            return int(x[:-1], 10) * 1024 * 1024
        elif x.startswith('0x') or x.startswith('0X'):
            return int(x, 16)
        else:
            return int(x, 10)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{x}' not a invalid hex integer")


def main():
    parser = argparse.ArgumentParser(
        description='multi bin package to upgrade')

    parser.add_argument("output", type=str, help="output file")
    parser.add_argument("-m", "--magic", type=type_val, default=0xBDAC9ADE,
                        help="magic for firmware check (default: 0xBDAC9ADE)")
    parser.add_argument("-l", "--limit", type=type_hex, default=0,
                        help="output file size limit (default: 0 => no limit)")
    parser.add_argument("-b", "--bin", type=str, action='append', default=[],
                        help="bin file list")

    args = parser.parse_args()

    if len(args.bin) == 0:
        error("please input bin file")

    upkgbin(args)


if __name__ == '__main__':
    main()
