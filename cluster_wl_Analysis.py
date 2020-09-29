"""
Plot WL of inter- and intra-clusters.

Usage:
    cluster_wl_Analysis.py.py     [-d <dir>]
    cluster_wl_Analysis.py.py     --help

Options:
    -d <file>   Dir containing the clusters
    -h --help   Print this help
"""
from docopt import docopt
import logging, logging.config
import re
import statistics
import math
import numpy as np
import os
import matplotlib.pyplot as plt
import datetime
from natsort import natsorted


if __name__ == "__main__":
    
    rootDir = ""
    args = docopt(__doc__)
    # print args
    fileName = ""
    if args["-d"]:
        rootDir = args["-d"]

    # Load base config from conf file.
    logging.config.fileConfig('log.conf')
    # Load logger from config
    logger = logging.getLogger('default')
    # Create new file handler
    fh = logging.FileHandler(os.path.join(rootDir, 'cluster_wl_analysis_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.log'))
    # Set a format for the file handler
    fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    # Add the handler to the logger
    logger.addHandler(fh)

    points = list()

    # Start with global nets
    os.chdir(rootDir)
    wl = list()
    with open(os.path.join(rootDir, "WLnets.out"), 'r') as f:
        lines = f.readlines()
    for line in lines[1:]:
        wl.append(float(line.split(' ')[2]))
    points.append([wl])
    logger.info("Global net WL average: {}, median: {}".format(statistics.mean(wl), statistics.median(wl)))

    for d in natsorted(os.listdir(rootDir)):
        clusterDir = os.path.join(rootDir, d)
        if os.path.isdir(clusterDir):
            os.chdir(clusterDir)
            wlInter = list()
            with open("inter-cluster_nets_wl.out", 'r') as f:
                lines = f.readlines()
            for line in lines:
                wlInter.append(float(line.split(', ')[1]))
            logger.info("Level {} inter-cluster net WL average: {}, median: {}".format(clusterDir.split('_')[-1], statistics.mean(wlInter), statistics.median(wlInter)))
            wlIntra = list()
            with open("intra-cluster_nets_wl.out", 'r') as f:
                lines = f.readlines()
            for line in lines:
                wlIntra.append(float(line.split(', ')[1]))
            points.append([wlInter, wlIntra])
            logger.info("Level {} intra-cluster net WL average: {}, median: {}".format(clusterDir.split('_')[-1], statistics.mean(wlIntra), statistics.median(wlIntra)))

    os.chdir(rootDir)


    filenameInfo = "{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    labels = list()

    plt.figure()
    plt.title("Nets WL, inter-cluster (left) and intra-cluster (right)\nDepending on clustering level")
    flierprops = dict(marker='o', markersize=1, linestyle='none')
    cnt = 0
    for i, data in enumerate(points):
        plt.boxplot(data, positions=[(cnt+y+i) for y in range(len(data))], showmeans=True, meanline=True, flierprops=flierprops)
        cnt += len(data)
    plt.xticks([0, 2.5, 5.5, 8.5, 11.5, 14.5, 17.5], ["Global", "1", "2", "3", "4", "5", "6"])
    plt.savefig('{}_cluster_WL.png'.format(filenameInfo))
    plt.savefig('{}_cluster_WL.pdf'.format(filenameInfo))
    plt.show()


