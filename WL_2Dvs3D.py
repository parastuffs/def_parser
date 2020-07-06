"""
Plot WL of 3D nets.

Usage:
    WL_2Dvs3D.py     [-w <WLnets.out>] [-n <connectivity_partition.txt file>]
    WL_2Dvs3D.py     --help

Options:
    -w <file>   List of nets and their WL
    -n <file>   List of cut nets
    -h --help   Print this help

Details:
The nets WL file should be as follows (with one header line):
<net name> <number of pins [int]> <Length [float]>

The connectivity partition file should be as follow:
<Amount of clusters> clusters, <Total number of nets> graphTotNets, <weight i> <number of n nets cut>, <net cut 1>, ... <net cut n>

"""
from docopt import docopt
import re
import statistics
import math
import numpy as np
import os
import matplotlib.pyplot as plt


def Evaluate3Dwl(wlFile, netCutFile):
    '''

    Parameters
    ----------
    wlFile : Str
        Path to wl file

    netCutFile : Str
        Path to net cut file

    Return
    ------
    N/A
    '''
    nets = dict() # {Net name : net wl}
    nets3D = dict() # {Net name : net wl}
    with open(wlFile, 'r') as f:
        lines = f.readlines()
    for line in lines[1:]:
        nets[line.split(' ')[0]] = float(line.split(' ')[2])

    with open(netCutFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        for el in line.split(',')[3:]:
            nets3D[el.strip()] = nets[el.strip()]

    points = list()
    tmp = list()
    for p in nets.values():
        tmp.append(p)
    points.append(tmp)

    tmp = list()
    for p in nets3D.values():
        tmp.append(p)
    points.append(tmp)

    plt.figure()
    plt.title("Wirelength of (left) 2D nets and (right) cut nets")
    plt.boxplot(points)
    plt.show()



if __name__ == "__main__":
    
    args = docopt(__doc__)
    # print args
    wlFile = "/home/para/dev/def_parser/2020-07-02_15-00-10_ldpc-2020_kmeans-geometric/WLnets.out"
    netCutFile = "/home/para/dev/def_parser/2020-07-02_15-00-10_ldpc-2020_kmeans-geometric/ldpc_routed_kmeans-geometric_1024/partitions_2020-07-02_15-02-39_hMetis/connectivity_partition.txt"
    if args["-w"]:
        wlFile = args["-w"]
    if args["-n"]:
        netCutFile = args["-n"]

    Evaluate3Dwl(wlFile, netCutFile)







