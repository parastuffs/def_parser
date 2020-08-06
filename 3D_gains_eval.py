"""
Usage:
    3D_gains_eval.py   [-d <dir>] [-c <folder 1,...,foler n>] [-q]
    3D_gains_eval.py (--help|-h)

Options:
    -d <dir>        Cluster directory, full path
                    e.g /full/path/date_time_design_method
    -c <folder 1,...,folder n >
                    Clustering subfolders
                    e.g flipr_hierarchical-geometric_2
    -q              Quiet mode (no graphical output)
    -h --help       Print this help
"""

from docopt import docopt
import os
import sys
import logging, logging.config
import datetime
import math
import statistics
import numpy as np
from Classes.Cluster import *
from Classes.Gate import *
from Classes.Net import *
import locale
import matplotlib.pyplot as plt
from alive_progress import alive_bar
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')


GATE_F = "CellCoord.out"
NET_F = "WLnets.out"
NET_GATE_F = "CellCoord.out"
NET_HPL_F = "hpl.out"
PART_DIRECTIVES_EXT = ".part" # Partitioning directives file extension
GATE_SIZES_F = "CellSizes.out"
PART_BASENAME = "" # e.g metis_01_NoWires_area"

NET_3D_OVERHEAD = 0

FORBIDEN_DIRS = ["ldpc_random_0", "old"]

def extractGates(file):
    """
    The input file is expected to be formated as follows:
        <net name>, <gate name>, <gate x>, <gate y>

    Parameters
    ----------
    file : str
        Path to input file

    Return
    ------
    gates : dict
        Dictionary of Gate objects
    """
    gates = dict()
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        gateName = line.split(',')[1]
        gates[gateName] = Gate(gateName)
        gates[gateName].setX(float(line.split(',')[2]))
        gates[gateName].setY(float(line.split(',')[3]))
    return gates

def extractGatesSize(file, gates):
    """
    The input file is expected to be formated as follows:
        <gate name>, <gate width [float]>, <gate height [float]>
    First line is a header.

    Parameters
    ----------
    file : str
        Path to input file
    gates : dict
        Dictionary {Gate.name : Gate}

    Return
    ------
    N/A
    """
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        line = line.strip()
        gateName = line.split(' ')[0]
        gates[gateName].setWidth(float(line.split(' ')[1]))
        gates[gateName].setHeight(float(line.split(' ')[2]))

def extractNets(file):
    """
    The input file is expected to be formated as follows:
        <net name> <number of pins> <length>
    The first line is the header:
        NET  NUM_PINS  LENGTH

    Parameters
    ----------
    file : str
        Path to input file

    Return
    ------
    nets : dict
        Dictionary of Net objects
    """
    nets = dict()
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        line = line.strip()
        netName = line.split(' ')[0]
        nets[netName] = Net(netName)
        nets[netName].setLength(float(line.split(' ')[2]))
    return nets

def gateNetAssociation(file, nets, gates):
    """
    The input file is expected to be formated as follows:
        <net name>, <gate name>, <gate x>, <gate y>

    Parameters
    ----------
    file : str
        Path to input file
    nets : dict
        Dictionary of Net objects
    gates : dict
        Dictionary of Gate objects

    Return
    ------
    N/A
    """
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        netName = line.split(',')[0]
        gateName = line.split(',')[1]
        nets[netName].addGate(gates[gateName])
        gates[gateName].addNet(nets[netName])

def NetHPL(file, nets):
    """
    Extract HPL info from file.
    File should be formated as follows:
        <net name [str]> <net HPL [float]> <Bounding box x1> <y1> <x2> <y2>
    e.g.
        load 62.928000000000004 0.882 3.68 17.346 50.144

    Parameters
    ----------
    file : str
        Path to input file
    nets : dictionary
        {Net.name : Net}

    Return
    ------
    N/A
    """
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        lineEl = line.split()
        nets[lineEl[0]].hpl = float(lineEl[1])
        nets[lineEl[0]].bb = [ [float(lineEl[2]), float(lineEl[3])], [float(lineEl[4]), float(lineEl[5])] ]

def gateLayer(file, gates):
    """
    Extract 3D layer information from file.
    File should be formated as follows:
        <gate name [str]> <layer [int]>
    e.g.
        FE_RC_3974_0 1

    Parameters
    ----------
    file : str
        Path to input file
    gates : dictionary
        {Gate.name : Gate}

    Return
    ------
    N/A
    """
    global PART_BASENAME
    PART_BASENAME = os.path.basename(file).split(".")[0]
    with open(file,'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        lineEl = line.split()
        gates[lineEl[0]].layer = int(lineEl[1])
        # logger.debug("Layer: {}".format(int(lineEl[1])))

def netLayer(nets):
    """
    Determine if the net is 3D or not.

    Parameters
    ----------
    nets : dict
        {Net.name : Net}
    
    Return
    ------
    N/A
    """
    for net in nets.values():
        # logger.debug("Net: {}".format(net.name))
        layer = -1
        net.is3d = 0 # reset
        for gate in net.gates.values():
            # logger.debug("Layer: {}".format(layer))
            if layer == -1:
                layer = gate.layer
            elif layer != gate.layer:
                net.is3d = 1
                # logger.debug("Net detected as 3D: {}".format(net.name))
                break
        net.layer = layer

def Approx_3D_HPL(gates, nets):
    """
    Approximate the HPL for all nets, after partitioning.

    Parameters
    ----------
    gates : dict
        {Gate.name : Gate}
    nets : dict
        {Net.name : Net}

    Return
    ------
    float
        Result of (HPL2D - HPL3D)/HPL2D
    """

    gains = [] # list of hpl2D - hpl3D

    gatesNested = {} # Dictionary of dictionaries: {Gate.x : {Gate.y : Gate.name}}
    for gate in gates.values():
        if gate.x not in gatesNested.keys():
            gatesNested[gate.x] = {gate.y : gate.name}
        else:
            gatesNested[gate.x][gate.y] = gate.name
    # print(gatesNested)
    hplStr = "net, HPL2D, HPL3D, Gain (HPL2D - HPL3D)/HPL2D, WL2D, is 3D\n"
    hplStrFilename = "{}_NetHPL3D.out".format(PART_BASENAME)

    i = 0
    with alive_bar(len(nets)) as bar:
        for net in nets.values():
            i += 1
            if net.hpl > 0:
                # net.hpl3d = net.hpl
                # hpl3d0 = net.hpl3d # HPL for the layer 0 of a 3D net
                # hpl3d1 = net.hpl3d # HPL for the layer 1 of a 3D net

                # Substracting the sqrt(gate.width * gate.height) from the hpl would result in negative values for hpl3d. It seems more accurate to remove the area of the cells from the area of the BB.
                bbArea = (net.bb[1][0] - net.bb[0][0]) * (net.bb[1][1] - net.bb[0][1])
                bbArea3d = bbArea
                bbArea3d0 = bbArea
                bbArea3d1 = bbArea

                DEBUG = False

                # if net.name == "ALUMemExeUnit/fdivsqrt_downvert_d2s_RoundRawFNToRecFN_n_4632":
                #     DEBUG = True

                # if DEBUG:
                #     logger.debug("{}, BB area: {}, Gate cumul area: {}".format(net.name, (net.bb[1][1]-net.bb[0][1]) * (net.bb[1][0]-net.bb[0][0]), sum([x.width*x.height for x in net.gates.values()])))

                for gateX in gatesNested.keys():
                    if gateX < net.bb[1][0] and gateX >= net.bb[0][0]:
                        for gateY in gatesNested[gateX].keys():
                            if gateY < net.bb[1][1] and gateY >= net.bb[0][1]:

                                gate = gates[gatesNested[gateX][gateY]]

                                # Gate not in the net, remove it from the bb
                                if gate not in net.gates.values():

                                    # if DEBUG:
                                    #     logger.debug("Considering gate {} {}".format(gate.name, gate))

                                    width = gate.width
                                    height = gate.height

                                    if ( (gate.x + gate.width) > net.bb[1][0]):
                                        # logger.warning("Gate {} is too wide, truncating...".format(gate.name))
                                        width = net.bb[1][0] - gate.x
                                    if ( (gate.y + gate.height) > net.bb[1][1]):
                                        # logger.warning("Gate '{}' is too tall, truncating...".format(gate.name))
                                        height = net.bb[1][1] - gate.y


                                    # 2D net
                                    if net.is3d == 0:
                                        # gate has moved to the other layer
                                        if gate.layer != net.layer:
                                            # net.hpl3d -= math.sqrt(gate.width * gate.height)
                                            bbArea3d -= width * height

                                    # 3D net
                                    elif net.is3d == 1:
                                        # Layer 0
                                        if gate.layer == 1:
                                            # hpl3d0 -= math.sqrt(gate.width * gate.height)
                                            bbArea3d0 -= width * height
                                            # if bbArea3d0 < 0:
                                            #     logger.error("3D BB area on layer 0 negative ({}) for net '{}'".format(bbArea3d0, net.name))
                                                # sys.exit()
                                        elif gate.layer == 0:
                                            # hpl3d1 -= math.sqrt(gate.width * gate.height)
                                            bbArea3d1 -= width * height
                                            # if bbArea3d1 < 0:
                                            #     logger.error("3D BB area on layer 1 negative ({}) for net '{}'".format(bbArea3d1, net.name))
                                                # sys.exit()
                                    else:
                                        logger.error("Unexpected value of net.is3d: '{}'".format(net.is3d))
                                        sys.exit()
                                else:
                                    # logger.debug("Skipping {} for net {}".format(gate.name, net.name))
                                    # Gate is in the net. Remove it from the BB3D on the opposite layer.
                                    # There shouldn't be any oob error has the BB is computed on their dimensions.
                                    if net.is3d == 1:
                                        if gate.layer == 1:
                                            bbArea3d0 -= gate.width * gate.height
                                        elif gate.layer == 0:
                                            bbArea3d1 -= gate.width * gate.height
                                        else:
                                            logger.error("Unexpected gate layer value {} for {}".format(gate.layer, gate.name))
                # End of net, add overhead if appropriate
                if net.is3d:
                    # logger.debug("Net is 3D: {}".format(net.name))
                    # net.hpl3d = hpl3d0 + hpl3d1 + NET_3D_OVERHEAD
                    if bbArea3d0 < 0:
                        logger.error("3D BB area on layer 0 negative ({}) for net '{}'".format(bbArea3d0, net.name))
                        bbArea3d0 = 0

                    if bbArea3d1 < 0:
                        logger.error("3D BB area on layer 1 negative ({}) for net '{}'".format(bbArea3d1, net.name))
                        bbArea3d1 = 0
                    net.hpl3d = 2*math.sqrt(bbArea3d0) + 2*math.sqrt(bbArea3d1) + NET_3D_OVERHEAD
                else:
                    # logger.debug("Net is NOT 3D: {}".format(net.name))
                    if bbArea3d < 0:
                        logger.error("2D negative ({}) for net '{}'".format(bbArea3d, net.name))
                        bbArea3d = 0
                    net.hpl3d = 2*math.sqrt(bbArea3d)
                gains.append((net.hpl - net.hpl3d)/net.hpl)
                if net.hpl3d < 0:
                    logger.warning("3D HPL for {} is {}, 2D was {}".format(net.name, net.hpl3d, net.hpl))

                            # logger.debug("Net {}, found gate {} in BB {}, coordinates: ({}, {})".format(net.name, gate.name, net.bb, gate.x, gate.y))
                hplStr += "{}, {}, {}, {}, {}, {}\n".format(net.name, net.hpl, net.hpl3d, gains[-1], net.wl, str(net.is3d))
            bar()
    logger.debug("Done.")
    logger.info("Average gain over HPL: {}".format(statistics.mean(gains)))
    logger.info("Exporting HPL to {}".format(hplStrFilename))
    with open(hplStrFilename, 'w') as f:
        f.write(hplStr)
    plt.figure()
    plt.title("(HPL 2D - HPL 3D) / HPL 2D")
    plt.boxplot(gains)
    plt.savefig('{}_3DHPL_gains.png'.format(PART_BASENAME))
    # plt.show()
    # sys.exit()    
    return statistics.mean(gains)


if __name__ == "__main__":

    args = docopt(__doc__)
    print(args)
    rootDir = ""
    clusteringGrains = None
    if args["-d"]:
        rootDir = args["-d"].rstrip('/')
    if args["-c"]:
        clusteringGrains = list(args["-c"].split(","))

    # Load base config from conf file.
    logging.config.fileConfig('log.conf')
    # Load logger from config
    logger = logging.getLogger('default')
    # Create new file handler
    fh = logging.FileHandler(os.path.join(rootDir, '3D_gains_eval_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.log'))
    # Set a format for the file handler
    fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    # Add the handler to the logger
    logger.addHandler(fh)

    if rootDir == "":
        logger.warning("No directory specified")

    try:
        design = rootDir.split(os.sep)[-1].split('_')[2]
    except:
        design = "Design not found"
        logger.error(design)
        sys.exit()
    try:
        method = rootDir.split(os.sep)[-1].split('_')[3]
    except:
        method = "Method not found"
        logger.error(method)
        sys.exit()

    logger.info("> Design: {}".format(design))
    logger.info("> method: {}".format(method))

    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

    logger.info("Extracting gates")
    gates = extractGates(os.path.join(rootDir, GATE_F))
    logger.info("Extracting gate sizes")
    extractGatesSize(os.path.join(rootDir, GATE_SIZES_F), gates)
    logger.info("Extracting nets")
    nets = extractNets(os.path.join(rootDir, NET_F))
    logger.info("Associate gates and nets")
    gateNetAssociation(os.path.join(rootDir, NET_GATE_F), nets, gates)
    logger.info("Retrieving HPL info from {}".format(NET_HPL_F))
    NetHPL(os.path.join(rootDir, NET_HPL_F), nets)

    meanGains = {} # {clust_folder/part_folder/part_file : average HPL gain}

    subdirToExplore = []
    if clusteringGrains == None:
        subdirToExplore = os.listdir(rootDir)
    else:
        subdirToExplore = clusteringGrains

    # logger.debug("clusteringGrains: {}".format(clusteringGrains))
    # logger.debug("subdirToExplore: {}".format(subdirToExplore))

    # Top dir, e.g 2019-02-07_15-12-26_flipr_hierarchical-geometric
    for d in subdirToExplore:
        subdir = os.path.join(rootDir, d)
        if os.path.isdir(subdir) and d not in FORBIDEN_DIRS:
            os.chdir(subdir)
            logger.info("Working in folder {}".format(d))
            # Clustering dir, e.g flipr_hierarchical-geometric_2
            for sd in os.listdir(subdir):
                subsubdir = os.path.join(subdir, sd)
                if os.path.isdir(subsubdir):
                    os.chdir(subsubdir)
                    logger.info("Working in partition folder {}".format(sd))
                    # Partitioning dir, e.g partitions_2020-07-23_10-11-46_hMetis
                    for pf in os.listdir(subsubdir):
                        if pf.endswith(PART_DIRECTIVES_EXT):
                            pf = os.path.join(subsubdir, pf)
                            if os.path.isfile(pf):
                                logger.info("Retrieving gate layer from {}".format(pf))
                                gateLayer(pf, gates)
                                logger.info("Determining if nets are 3D.")
                                netLayer(nets)
                                logger.info("Approximating 3D HPL")
                                meanGains["{}/{}/{}".format(d, sd, pf)] = Approx_3D_HPL(gates, nets)
            # logger.info("Extracting clusters")
            # clusters = extractClusters(os.path.join(subdir, CLUSTER_F))
            # logger.info("Associate clusters and gates")
            # clusterGateAssociation(os.path.join(subdir, CLUSTER_GATE_F), clusters, gates)
            # clusterConnectivity(clusters, nets)
            # silouhette(clusters, gates)
    logger.info("Average gains: {}".format(meanGains))