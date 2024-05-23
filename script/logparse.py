#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ./logp.py <inputfile> <outputfile> [--logstr .logstr] [--realtime] [--magic 0xD6]

import os
import argparse
import struct
from datetime import datetime

'''
typedef struct MDS_LOG_Compress {
    uint8_t magic;
    uint32_t address   : 24;  // 0xFFxxxxxx
    uint32_t level     : 4;
    uint32_t count     : 4;
    uint32_t psn       : 12;
    uint64_t timestamp : 44;  // ms
    uint32_t args[MDS_LOG_COMPRESS_ARGS_MAX];
} MDS_LOG_Compress_t;
'''


def log_struct(log, logstr):
    local_time = datetime.fromtimestamp(log["timestamp"] / 1000.0)
    string = "[" + local_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "]"

    level_str = ["NONE", "DIRT", "FATA", "ERRO", "WARN", "INFO", "DEBG"]
    if log["level"] < len(level_str):
        string += "[%s]" % level_str[log["level"]]
    else:
        string += "[UNKW]"

    string += "[psn:%.4d]" % log["psn"]

    ofs = log["address"]
    if ofs > len(logstr):
        string += "PARSE!!!: not find fmt on address:0x%x" % ofs
        return (False, string)

    fmt = logstr[ofs:ofs+1]

    chars = []
    while ofs < len(logstr):
        c = logstr[ofs:ofs+1]
        if c.encode('utf-8') == b'\x00':
            break
        chars.append(c)
        ofs += 1
    fmt = b''.join(map(lambda x: x.encode('utf-8'), chars)).decode('utf-8')

    try:
        string += fmt % tuple(log["args"])
        return (True, string)
    except:
        string += "PARSE!!!:" + fmt + " args:" + str(log["args"]) + "\n"
        return (False, string)


def log_parse(args):
    with open(args.infile, 'rb') as f:
        content = f.read()

    with open(args.logstr, 'r') as f:
        logstr = f.read()

    cnt = 0
    ofs = 0
    with open(args.outfile, 'w') as f:
        while (ofs+12) <= len(content):
            header = struct.unpack('>LLL', content[ofs:(ofs+12)])
            log = dict(
                magic=hex((header[0] >> 24) & 0xFF),
                address=(header[0] >> 0) & 0x00FFFFF,
                level=(header[1] >> 28) & 0xF,
                count=(header[1] >> 24) & 0xF,
                psn=(header[1] >> 12) & 0xFFF,
                timestamp=(header[1] & 0xFFF) << 32 | header[2],
                args=[],
            )
            if log["magic"] != hex(args.magic):
                ofs += 1
                continue

            next = ofs + 12 + log["count"] * 4
            if next > len(content):
                ofs += 1
                continue

            for i in range(log["count"]):
                arg = struct.unpack('<L', content[(ofs+12+i*4):(ofs+12+i*4+4)])
                log["args"].append(arg[0])
            ret = log_struct(log, logstr)
            f.write(ret[1])
            if ret[0] == False:
                ofs += 1
            else:
                cnt += 1
                ofs = next

    print('\033[32mFINISH:\033[0m %d logs parsed' % cnt)


def main():
    argparser = argparse.ArgumentParser(description='logp')

    argparser.add_argument('infile', help='input file')
    argparser.add_argument('-o', '--outfile', help='output file',
                           default=None)

    argparser.add_argument('-l', '--logstr', help='logstr',
                           default=os.path.abspath('.logstr'))

    argparser.add_argument('-r', '--realtime', help='realtime',
                           action='store_true')

    argparser.add_argument('--magic', help='magic', type=hex, default=0xD6)

    args = argparser.parse_args()

    args.infile = os.path.abspath(args.infile)
    if not os.path.exists(args.infile):
        print('\033[31mERROR:\033[0m input file not exist')
        exit(-1)

    if not os.path.exists(args.logstr):
        print('\033[31mERROR:\033[0m logstr file not exist')
        exit(-1)

    curr_time = datetime.now()
    fort_time = curr_time.strftime("%Y_%m_%d_%H_%M_%S")

    if (args.outfile == None):
        args.outfile = os.path.abspath(args.infile + '_%s.txt' % fort_time)

    log_parse(args)


if __name__ == '__main__':
    main()
