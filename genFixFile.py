#!/usr/bin/env python3

"""
Usage:
    genFixFile.py   [--top <int>] [--bot <int>] [--tot <int>]
                    [-d <dir>]
    genFixFile.py   (--help|-h)

Options:
    --top <int>     Number of cells fixed on top
    --bot <int>     Number of cells fixed on bottom
    --tot <int>     Total number of cells
    -d <dir>        Destination directory. Should be in the clustering dir.
    -h --help       Print this help
"""


import os
from docopt import docopt


if __name__ == "__main__":
    args = docopt(__doc__)

    top = 0
    bot = 0
    tot = 0
    outDir = os.getcwd()
    if args["--top"]:
        top = int(args["--top"])
    if args["--bot"]:
        bot = int(args["--bot"])
    if args["--tot"]:
        tot = int(args["--tot"])
    if args["-d"]:
        outDir = args["-d"]


    s = ""
    for i in range(top):
        s += "1\n"
    for i in range(bot):
        s += "0\n"
    for i in range(tot-top-bot):
        s += "-1"

    with open(os.path.join(outDir, "fixfile.hgr"), 'w') as f:
        f.write(s)