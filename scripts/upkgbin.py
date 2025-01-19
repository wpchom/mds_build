#!/usr/bin/python3

import os
import argparse
import hashlib
import struct


'''
#define MDS_BOOT_UPGRADE_MAGIC 0x9ADE

typedef struct MDS_BOOT_BinInfo {
    uint16_t check;
    uint16_t flag;
    uint32_t dstAddr;
    uint32_t srcSize;
    uint8_t hash[MDS_BOOT_CHKHASH_SIZE];

    // context of `uint8_t data[srcSize]` for upgrade bin
} MDS_BOOT_BinInfo_t;

typedef struct MDS_BOOT_UpgradeInfo {
    uint16_t check;  // check upgradeInfo header
    uint16_t magic;
    uint16_t type;   // type comfired for firmware
    uint16_t count;  // count of binInfos
    uint32_t size;   // totalSize
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


class BinFile:
    def __init__(self, path, addr, flag):
        if not os.path.exists(path):
            print(f"file {path} not exist")
            exit(-1)

        if flag < 0 or flag > 0xFFFF:
            print(f"flag {flag} out of range")
            exit(-1)

        self.path = path
        self.flag = flag
        self.addr = addr
        self.size = os.path.getsize(path)
        self.hash = hashlib.sha256(open(path, 'rb').read()).digest()

        self.header = struct.pack('>H', self.flag) + \
            struct.pack('>II', self.addr, self.size) + self.hash
        self.check = crc16(self.header)
        self.header = struct.pack('>H', int(self.check)) + self.header


def hex_uint16(x):
    try:
        value = int(x, 16)
        if value < 0 or value > 0xFFFF:
            raise ValueError()
        else:
            return int(x, 16)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{x}' not a uint16 hex integer")


def main():
    parser = argparse.ArgumentParser(
        description='multi bin package to upgrade')

    parser.add_argument("output", type=str, help="output file")
    parser.add_argument("-m", "--magic", type=hex_uint16, default=0x9ADE,
                        help="magic number")
    parser.add_argument("-t", "--type", type=hex_uint16, default=0x0000,
                        help="type comfired for firmware")
    parser.add_argument("-b", "--bin", type=str, action='append', default=[],
                        help="bin file list")

    args = parser.parse_args()

    if len(args.bin) == 0:
        print("please input bin file")
        exit(-1)

    bin_count = 0
    total_size = 0
    upgrade_hash = hashlib.sha256()
    bin_list = []
    for bin in args.bin:
        bin_count += 1
        path = os.path.abspath(bin.split(',')[0])
        addr = int(bin.split(',')[1], 16)
        flag = int(bin.split(',')[2], 16)
        b = BinFile(path, addr, flag)
        total_size += b.size + len(b.header)
        upgrade_hash.update(b.header)
        upgrade_hash.update(open(path, 'rb').read())
        bin_list.append(b)

    upgrade_header = struct.pack('>HHH', args.magic, args.type, bin_count) + \
        struct.pack('>I', total_size) + upgrade_hash.digest()
    upgrade_check = crc16(upgrade_header)
    upgrade_header = struct.pack('>H', int(upgrade_check)) + upgrade_header

    print(f'[upkgbin] count:{bin_count} into:{args.output}')
    with open(args.output, 'wb') as f:
        f.write(upgrade_header)
        for b in bin_list:
            f.write(b.header)
            f.write(open(b.path, 'rb').read())
            print(f'''- bin:{b.path}, addr:{hex(b.addr)}, flag:{
                  hex(b.flag)}, size:{b.size}''')
        f.close()


if __name__ == '__main__':
    main()
