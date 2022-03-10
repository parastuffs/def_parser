"""
Usage:
    compare_netlists.py     [-a <netlistA>] [-b <netlistB>]
    compare_netlists.py     (--help|-h)

Options:
    -a <netlistA>       Path to netlist A
    -b <netlistB>       Path to netlist B
    -h --help           Print this help
"""

import os
from alive_progress import alive_bar
from docopt import docopt

# FILE_A = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile_flat_synth/tile_flat_instances.csv"
# FILE_A = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile/forQD/tile_withBuffers_instances.csv"
# FILE_B = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile/forQD/tile_noBuffers_instances.csv"
# FILE_B = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile/forQD/tile_withBuffers_instances.csv"
# FILE_B = "/home/para/dev/def_parser/MemPool/tilePnR_2021-05-05/tile_noBuff_instances.csv"

if __name__ == "__main__":
    args = docopt(__doc__)

    if args["-a"]:
        FILE_A = args["-a"]
    if args["-b"]:
        FILE_B = args["-b"]

    instancesA = set()
    instancesB = set()

    with open(FILE_A, 'r') as f:
        lines = f.readlines()
    for line in lines[1:]:
        instancesA.add(line.split(',')[1])

    with open(FILE_B, 'r') as f:
        lines = f.readlines()
    for line in lines[1:]:
        instancesB.add(line.split(',')[1])

    print("A is {}".format(FILE_A.split(os.sep)[-1]))
    print("B is {}".format(FILE_B.split(os.sep)[-1]))
    print("Total instances A: {}".format(len(instancesA)))
    print("Total instances B: {}".format(len(instancesB)))
    print("Instances in A, but not in B: {}".format(len(instancesA-instancesB)))
    print("Instances in B, but not in A: {}".format(len(instancesB-instancesA)))
    print("Instances in both A and B: {}".format(len(instancesB&instancesA)))
