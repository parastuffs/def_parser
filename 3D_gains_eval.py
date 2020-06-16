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
    print("coucou")
    gatesPosition = {} # {position : Gate.name}

    for gate in gates.values():
        gatesPosition[gate.x + (gate.y * width)] = gate.name
        # print(gate.x, gate.y)
    gatesPositionsSorted = sorted(gatesPosition.keys())
    # print(gatesPositionsSorted)

    UNITS_DISTANCE_MICRONS = 10000

    for net in nets.values():
        print(net.bb)
        for y in range(int(net.bb[0][1]*UNITS_DISTANCE_MICRONS), int(net.bb[1][1]*UNITS_DISTANCE_MICRONS)):
            for x in range(int(net.bb[0][1]*UNITS_DISTANCE_MICRONS), int(net.bb[1][0]*UNITS_DISTANCE_MICRONS)):
                coordinate = x + (width*y)
                # print(coordinate)
                if coordinate/UNITS_DISTANCE_MICRONS in gatesPosition:
                    logger.debug("Net {}, found gate {} in BB".format(net.name, gatesPosition[coordinate/UNITS_DISTANCE_MICRONS]))


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
    logger.info("Extracting nets")
    nets = extractNets(os.path.join(rootDir, NET_F))
    logger.info("Associate gates and nets")
    gateNetAssociation(os.path.join(rootDir, NET_GATE_F), nets, gates)
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
                                Approx_3D_HPL(gates, nets, designWidths[design])
            # logger.info("Extracting clusters")
            # clusters = extractClusters(os.path.join(subdir, CLUSTER_F))
            # logger.info("Associate clusters and gates")
            # clusterGateAssociation(os.path.join(subdir, CLUSTER_GATE_F), clusters, gates)
            # clusterConnectivity(clusters, nets)
            # silouhette(clusters, gates)
