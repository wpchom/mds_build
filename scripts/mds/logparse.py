#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import struct
import datetime

sys.dont_write_bytecode = True

from build import error, debug


def parser(subparsers):
    parser = subparsers.add_parser(
        "logparse", aliases=["g"], help="compress log parser"
    )

    parser.add_argument("infile", help="input file")
    parser.add_argument(
        "-o",
        "--outfile",
        default=None,
        help="output file for log parse",
    )

    parser.add_argument(
        "-l",
        "--logstr",
        default=os.path.abspath(".logstr"),
        help="logstr file",
    )

    parser.add_argument(
        "-b",
        "--big-endian",
        action="store_true",
        default=False,
        help="big endian for log bin",
    )

    parser.add_argument(
        "--magic",
        type=hex,
        default=0xD6,
        help="magic number default:0xD6",
    )

    parser.add_argument("-v", "--verbose", action="store_true", default=False)


def action(args):
    args.infile = os.path.abspath(args.infile)
    if not os.path.exists(args.infile):
        error(f"input file `{args.infile}` not exist")

    if not os.path.exists(args.logstr):
        error(f"logstr file `{args.logstr}` not exist")

    curr_time = datetime.now()
    fort_time = curr_time.strftime("%Y_%m_%d_%H_%M_%S")

    if args.outfile == None:
        args.outfile = os.path.abspath(args.infile + "_%s.txt" % fort_time)

    log_parser(args)


def _log_struct(log, logstr):
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

    fmt = logstr[ofs : ofs + 1]

    chars = []
    while ofs < len(logstr):
        c = logstr[ofs : ofs + 1]
        if c.encode("utf-8") == b"\x00":
            break
        chars.append(c)
        ofs += 1
    fmt = b"".join(map(lambda x: x.encode("utf-8"), chars)).decode("utf-8")

    try:
        string += fmt % tuple(log["args"])
        return (True, string)
    except Exception:
        string += "PARSE!!!:" + fmt + " args:" + str(log["args"]) + "\n"
        return (False, string)


def log_parser(args):
    with open(args.infile, "rb") as f:
        content = f.read()

    with open(args.logstr, "r") as f:
        logstr = f.read()

    cnt = 0
    ofs = 0
    with open(args.outfile, "w") as f:
        while (ofs + 12) <= len(content):
            if args.big_endian:
                magic, header = struct.unpack(">BI", content[ofs : ofs + 5])
                timestamp = int.from_bytes(content[ofs + 5 : ofs + 12], byteorder="big")
            else:
                magic, header = struct.unpack("<BI", content[ofs : ofs + 5])
                timestamp = int.from_bytes(
                    content[ofs + 5 : ofs + 12], byteorder="little"
                )

            log = dict(
                magic=magic,
                address=header & 0xFFFFFF,
                level=(header >> 24) & 0xF,
                count=(header >> 28) & 0xF,
                psn=(header >> 32) & 0xFFF,
                timestamp=timestamp,
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
                arg = struct.unpack(
                    "<L", content[(ofs + 12 + i * 4) : (ofs + 12 + i * 4 + 4)]
                )
                log["args"].append(arg[0])
            ret = _log_struct(log, logstr)
            f.write(ret[1])
            if ret[0] == False:
                ofs += 1
            else:
                cnt += 1
                ofs = next

    debug(f"`{args.outfile}` parser log cnt:{cnt}")
