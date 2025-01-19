#!/usr/bin/python3

import lzma
import argparse


def main():
    parser = argparse.ArgumentParser(description='LZMA compression')

    parser.add_argument('input', help='file to compress')
    parser.add_argument('output', help='output file')

    parser.add_argument("--format", type=str, default="lzma", choices=["lzma", "xz"],
                        help="compression format (default: lzma)")
    parser.add_argument("--dict_size", type=int, default=4096,
                        help="dictionary size (default: 4096)")
    parser.add_argument("--lc", type=int, default=1,
                        help="literal context bits (default: 1)")
    parser.add_argument("--lp", type=int, default=1,
                        help="literal position bits (default: 1)")
    parser.add_argument("--pb", type=int, default=1,
                        help="position bits (default: 1)")
    parser.add_argument("--nice_len", type=int, default=273,
                        help="nice length (default: 273)")
    parser.add_argument("--depth", type=int, default=0,
                        help="depth (default: 0)")

    args = parser.parse_args()

    if (args.format == "lzma"):
        filter = {
            'id':  lzma.FILTER_LZMA1,
            'dict_size': args.dict_size,
            'lc': args.lc,
            'lp': args.lp,
            'pb': args.pb,
            'nice_len': args.nice_len,
            'depth': args.depth,
        }
        compressor = lzma.LZMACompressor(lzma.FORMAT_ALONE, filters=[filter])
    else:
        print("not support format")
        exit(-1)

    fin = open(args.input, 'rb')
    fout = open(args.output, 'wb')
    fout.write(compressor.compress(fin.read()))
    fout.write(compressor.flush())
    fin.close()
    fout.close()


if __name__ == '__main__':
    main()
