"""
Usage:
    cluster_analysis.py   [-d <dir>]
    cluster_analysis.py (--help|-h)

Options:
    -d <dir>        Cluster directory
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

NET_3D_OVERHEAD = 0

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
        <net name [str]> <net HPL [float]>
    e.g.
        load 62.928000000000004

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
    with open(file,'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        lineEl = line.split()
        gates[lineEl[0]].layer = int(lineEl[1])

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
        layer = -1
        for gate in net.gates.values():
            if layer == -1:
                layer = gate.layer
            elif layer != gate.layer:
                net.is3d = 1
                break
        net.alyer = layer

def Approx_3D_HPL(gates, nets, width):
    """
    Approximate the HPL for all nets, after partitioning.

    Parameters
    ----------
    gates : dict
        {Gate.name : Gate}
    nets : dict
        {Net.name : Net}
    width : int
        Width of the design in the same units as the gates coordinates.
    """
    gatesPosition = {} # {position : Gate.name}

    gains = [] # list of hpl2D - hpl3D

    for gate in gates.values():
        gatesPosition[gate.x + (gate.y * width)] = gate.name
        # print(gate.x, gate.y)
    gatesPositionsSorted = sorted(gatesPosition.keys())
    # print(gatesPositionsSorted)

    UNITS_DISTANCE_MICRONS = 1000

    gatesNested = {} # Dictionary of dictionaries: {Gate.x : {Gate.y : Gate.name}}
    for gate in gates.values():
        if gate.x not in gatesNested.keys():
            gatesNested[gate.x] = {gate.y : gate.name}
        else:
            gatesNested[gate.x][gate.y] = gate.name
    # print(gatesNested)

    i = 0
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

            for gateX in gatesNested.keys():
                if gateX < net.bb[1][0] and gateX > net.bb[0][0]:
                    for gateY in gatesNested[gateX].keys():
                        if gateY < net.bb[1][1] and gateY > net.bb[0][1]:

                            # 2D net
                            if net.is3d == 0:
                                # gate has moved to the other layer
                                if gate.layer != net.layer:
                                    # net.hpl3d -= math.sqrt(gate.width * gate.height)
                                    bbArea3d -= gate.width * gate.height

                            # 3D net
                            elif net.is3d == 1:
                                # Layer 0
                                if gate.layer == 1:
                                    # hpl3d0 -= math.sqrt(gate.width * gate.height)
                                    bbArea3d0 -= gate.width * gate.height
                                elif gate.layer == 0:
                                    # hpl3d1 -= math.sqrt(gate.width * gate.height)
                                    bbArea3d1 -= gate.width * gate.height
                            else:
                                logger.error("Unexpected value of net.is3d: '{}'".format(net.is3d))
                                sys.exit()
            # End of net, add overhead if appropriate
            if net.is3d:
                # net.hpl3d = hpl3d0 + hpl3d1 + NET_3D_OVERHEAD
                net.hpl3d = math.sqrt(bbArea3d0) + math.sqrt(bbArea3d1) + NET_3D_OVERHEAD
            else:
                net.hpl3d = math.sqrt(bbArea3d)
            gains.append((net.hpl - net.hpl3d)/net.hpl)
            if net.hpl3d < 0:
                logger.warning("3D HPL for {} is {}, 2D was {}".format(net.name, net.hpl3d, net.hpl))

                        # logger.debug("Net {}, found gate {} in BB {}, coordinates: ({}, {})".format(net.name, gate.name, net.bb, gate.x, gate.y))
    logger.debug("Done.")
    logger.info("Average gain over HPL: {}".format(statistics.mean(gains)))
    plt.title("(HPL 2D - HPL 3D) / HPL 2D")
    plt.boxplot(gains)
    plt.savefig('3DHPL_gains.png')
    plt.show()


if __name__ == "__main__":

    args = docopt(__doc__)
    print(args)
    rootDir = ""
    if args["-d"]:
        rootDir = args["-d"].rstrip('/')

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

    designWidths = {"ldpc":575820}

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
    logger.info("Determining if nets are 3D.")
    netLayer(nets)
    logger.info("Retrieving HPL info from {}".format(NET_HPL_F))
    NetHPL(os.path.join(rootDir, NET_HPL_F), nets)

    for d in os.listdir(rootDir):
        subdir = os.path.join(rootDir, d)
        if os.path.isdir(subdir):
            os.chdir(subdir)
            logger.info("Working in folder {}".format(d))
            for sd in os.listdir(subdir):
                subsubdir = os.path.join(subdir, sd)
                if os.path.isdir(subsubdir):
                    os.chdir(subsubdir)
                    logger.info("Working in partition folder {}".format(sd))
                    for pf in os.listdir(subsubdir):
                        if pf.endswith(PART_DIRECTIVES_EXT):
                            pf = os.path.join(subsubdir, pf)
                            if os.path.isfile(pf):
                                logger.info("Retrieving gate layer from {}".format(pf))
                                gateLayer(pf, gates)
                                logger.info("Approximating 3D HPL")
                                Approx_3D_HPL(gates, nets, designWidths[design])
            # logger.info("Extracting clusters")
            # clusters = extractClusters(os.path.join(subdir, CLUSTER_F))
            # logger.info("Associate clusters and gates")
            # clusterGateAssociation(os.path.join(subdir, CLUSTER_GATE_F), clusters, gates)
            # clusterConnectivity(clusters, nets)
            # silouhette(clusters, gates)
