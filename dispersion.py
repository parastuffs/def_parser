"""
Compute net dispersion based on exiting segmentation files.

Usage:
    boxplot.py     [-d <dir>]
    boxplot.py     --help

Options:
    -d <dir>    Path to folder containing WLnets.out and WLnets_segments.out
    -h --help   Print this help
"""
from docopt import docopt
import re
import statistics
import math
import numpy as np
import os
import matplotlib.pyplot as plt
import datetime
from alive_progress import alive_bar

WLNETS_F = "WLnets.out"
WLNETSSEGMENTS_F = "WLnets_segments.out"


if __name__ == "__main__":
    
    args = docopt(__doc__)
    # print args
    fileName = ""
    if args["-d"]:
        dirName = args["-d"]
    os.chdir(dirName)

    netWL = dict() # {net name : wirelength}
    netSegLen = dict() # {net name : [segment len]}
    dispersions = list()

    with open(os.path.join(dirName, WLNETS_F), 'r') as f:
        lines = f.readlines()

    print("Reading {}".format(WLNETS_F))
    with alive_bar(len(lines)-1) as bar:
        for line in lines[1:]:
            net = line.split()[0]
            fanout = int(line.split()[1])
            if fanout > 1:
                netWL[line.split()[0]] = float(line.split()[2])
            bar()

    with open(os.path.join(dirName, WLNETSSEGMENTS_F), 'r') as f:
        lines = f.readlines()

    print("Reading {}".format(WLNETSSEGMENTS_F))
    with alive_bar(len(lines)-1) as bar:
        for line in lines[1:]:
            net = line.split()[0].split('/')[0]
            if net in netSegLen.keys():
                netSegLen[net].append(float(line.split()[2]))
            else:
                netSegLen[net] = [float(line.split()[2])]
            bar()

    print("Computing dispersions.")
    with alive_bar(len(netWL)) as bar:
        for net in netWL.keys():
            segments = netSegLen[net]
            segments = [x/max(segments) for x in segments]
            wl = netWL[net]
            if len(segments) == 1:
                dispersions.append(sum([(1/x) for x in segments]))
            else:
                dispersions.append(sum([(1/x)/math.comb(len(segments),2) for x in segments]))
            bar()


    filenameInfo = "{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))


    # plt.figure(figsize=(7,4))
    plt.title("Wirelength distribution of all nets (2D) and cut nets (3D)")
    flierprops = dict(marker='o', markersize=1, linestyle='none')
    plt.boxplot(dispersions, showmeans=True, meanline=True, showfliers=True, flierprops=flierprops)
    # plt.xticks([i+1 for i in range(len(labels))],labels)
    plt.savefig('{}_NetSegments_concentration_boxplot.pdf'.format(filenameInfo))
    plt.show()


