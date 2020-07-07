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
    netsWL = dict() # {Net name : net wl}
    nets3DWL = dict() # {Net name : net wl}
    netsPins = dict() # {Net name : net pins}
    nets3DPins = dict() # {Net name : net pins}
    pinValues = set()
    with open(wlFile, 'r') as f:
        lines = f.readlines()
    for line in lines[1:]:
        netsWL[line.split(' ')[0]] = float(line.split(' ')[2])
        netsPins[line.split(' ')[0]] = int(line.split(' ')[1])
        pinValues.add(int(line.split(' ')[1]))

    with open(netCutFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        for el in line.split(',')[3:]:
            nets3DWL[el.strip()] = netsWL[el.strip()]
            nets3DPins[el.strip()] = netsPins[el.strip()]

    points = list()
    tmp = list()
    for p in netsWL.values():
        tmp.append(p)
    points.append(tmp)

    tmp = list()
    for p in nets3DWL.values():
        tmp.append(p)
    points.append(tmp)

    pinX = list(pinValues)
    pins2D = {}
    for p in pinX:
        pins2D[p] = 0
    for v in netsPins.values():
        pins2D[v] += 1
    pins2DPerc = [i/sum(pins2D.values()) for i in pins2D.values()]

    pins3D = {}
    for p in pinX:
        pins3D[p] = 0
    for v in nets3DPins.values():
        pins3D[v] += 1
    pins3DPerc = [i/sum(pins3D.values()) for i in pins3D.values()]

    plt.figure()
    plt.title("Wirelength of (left) 2D nets and (right) cut nets")
    plt.boxplot(points)

    plt.figure()
    plt.subplot(2,2,1)
    plt.title("Fanout of 2D nets")
    # plt.yscale("log")
    plt.bar(pinX, pins2D.values())
    plt.subplot(2,2,2)
    plt.title("Fanout of 3D cut nets")
    # plt.yscale("log")
    plt.bar(pinX, pins3D.values())
    plt.subplot(2,2,3)
    plt.title("Fanout of 2D nets (norm)")
    plt.bar(pinX, pins2DPerc)
    plt.subplot(2,2,4)
    plt.title("Fanout of 3D cut nets (norm)")
    plt.bar(pinX, pins3DPerc)

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







