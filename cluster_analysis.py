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
import logging, logging.config
import datetime
from Classes.Cluster import *
from Classes.Gate import *
from Classes.Net import *

GATE_F = "CellCoord.out"
CLUSTER_F = "ClustersArea.out"
NET_F = "WLnets.out"
NET_GATE_F = "CellCoord.out"
CLUSTER_GATE_F = "ClustersInstances.out"


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

def extractClusters(file):
    """
    The input file is expected to be formated as follows:
        <cluster id> <type> <number gates> (<x1>, <y1>) (<x2>, <y2>) <area>
    The first line is a header:
        Name Type InstCount Boundary Area

    Parameters
    ----------
    file : str
        Path to input file

    Return
    ------
    clusters : dict
        Dictionary of Cluster objects
    """
    clusters = dict()
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        line = line.strip()
        lineEl = line.split(' ')
        clusters[int(lineEl[0])] = Cluster(0, 0, float(lineEl[5]), (0,0), int(lineEl[0]))
        clusters[int(lineEl[0])].setGateArea(clusters[int(lineEl[0])].area)
    return clusters

def clusterGateAssociation(file, clusters, gates):
    """
    The input file is expected to be formated as follows:
        <cluster ID> <gate 1> ... <gate n>

    Parameters
    ----------
    file : str
        Path to input file
    clusters : dict
        Dictionary of Cluster objects
    gates : dict
        Dictionary of Gate objects
    """
    with open(file, 'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        lineSplit = line.split(' ')
        for l in lineSplit[1:]:
            clusters[int(lineSplit[0])].addGate(gates[l])
            gates[l].addCluster(clusters[int(lineSplit[0])])



if __name__ == "__main__":

    args = docopt(__doc__)
    print(args)
    rootDir = ""
    if args["-d"]:
        rootDir = args["-d"]

    # Load base config from conf file.
    logging.config.fileConfig('log.conf')
    # Load logger from config
    logger = logging.getLogger('default')
    # Create new file handler
    fh = logging.FileHandler(os.path.join(rootDir, 'cluster_analysis_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.log'))
    # Set a format for the file handler
    fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    # Add the handler to the logger
    logger.addHandler(fh)

    if rootDir == "":
        logger.warning("No directory specified")

    logger.info("vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
    logger.info("> Clustering analysis")

    try:
        design = rootDir.split(os.sep)[-1].split('_')[2]
    except:
        design = "Design not found"
    try:
        method = rootDir.split(os.sep)[-1].split('_')[3]
    except:
        method = "Method not found"

    logger.info("> Design: {}".format(design))
    logger.info("> method: {}".format(method))

    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

    c = Cluster(0,0,0,0,0)
    c.setGateArea(50)

    logger.info("Extracting gates")
    gates = extractGates(os.path.join(rootDir, GATE_F))
    logger.info("Extracting nets")
    nets = extractNets(os.path.join(rootDir, NET_F))
    logger.info("Associate gates and nets")
    gateNetAssociation(os.path.join(rootDir, NET_GATE_F), nets, gates)

    for d in os.listdir(rootDir):
        subdir = os.path.join(rootDir, d)
        if os.path.isdir(subdir):
            logger.info("Working in folder {}".format(subdir))
            logger.info("Extracting clusters")
            clusters = extractClusters(os.path.join(subdir, CLUSTER_F))
            logger.info("Associate clusters and gates")
            clusterGateAssociation(os.path.join(subdir, CLUSTER_GATE_F), clusters, gates)