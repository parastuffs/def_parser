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
import statistics
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
CLUSTER_F = "ClustersArea.out"
NET_F = "WLnets.out"
NET_GATE_F = "CellCoord.out"
CLUSTER_GATE_F = "ClustersInstances.out"


def manhattanDistance(a, b):
    """
    Parameters
    ----------
    a : arr
        Array of two float coordinates
    b : arr
        Array of two float coordinates

    Return
    ------
    Manhattan distance between a and b.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


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


def clusterConnectivity(clusters, nets):
    """
    Find out what is the inter-cluster connectivity.
    """

    RAW_INTERCONNECTIONS = False  # If True, we don't care to which clusters a cluster is connected.
                                # All we care about is that it's establishing an inter-cluster connection.
                                # In that case, all clusters are connected to a cluster "0" which corresponds to none cluster ID (they begin at 1).
                                # If this is true, we go from an O(n^2) algo (loop twice on all clusters) to a O(n).

    logger.info("Establish connectivity")
    connectivity = dict() # Key: source cluster, values: destination clusters
    connectivityUniqueNet = dict() # Connectivity, but counting only once every net between clusters

    # In this matrix, a 0 means no connection.
    # conMatrix = [[0 for x in range(clustersTotal)] for y in range(clustersTotal)]
    # conMatrixUniqueNet = [[0 for x in range(clustersTotal)] for y in range(clustersTotal)]
    
    clusterNetSet = dict() # Dictionary of sets.

    spaningNetsUnique = dict() # This dicitonary contains all the nets that span over more than one cluster. The difference with the other dictionaries is that this one contains each net only once. This will be used to compute the total inter-cluster wirelength.

    clustersTotal = len(clusters)

    interNets = dict() # Net spanning several clusters {Net.name : Net}
    intraNets = dict() # Net fully contained in a single cluster {Net.name : Net}

    for ck in clusters:
        cluster = clusters[ck]
        connectivity[cluster.id] = []
        connectivityUniqueNet[cluster.id] = []
        clusterNetSet[cluster.id] = set()
        clusterGateArea = 0 # Cumulated area of the gates in the cluster
        # print "Source cluster: " + str(cluster.id)
        for key in cluster.gates:
            gateName = cluster.gates[key].name
            for netKey in cluster.gates[key].nets:
                net = cluster.gates[key].nets[netKey]
                for subkey in net.gates:
                    subgateName = net.gates[subkey].name
                    if RAW_INTERCONNECTIONS:
                        # Simply check that the gate selected is not in the same cluster.
                        if cluster.gates.get(subgateName) == None:
                            connectivity[cluster.id].append(0)
                            if netKey not in clusterNetSet[cluster.id]:
                                # If the net is not yet registered in the cluster, add it.
                                clusterNetSet[cluster.id].add(netKey)
                                connectivityUniqueNet[cluster.id].append(0)
                                if spaningNetsUnique.get(netKey) == None:
                                    # If the net is not registered as spaning over several clusters, add it.
                                    spaningNetsUnique[netKey] = net
                                    interNets[net.name] = net

                    else:
                        if net.gates[subkey].cluster.id != cluster.id:
                            if net.gates[subkey].cluster.gates.get(subgateName) != None:
                                    connectivity[cluster.id].append(net.gates[subkey].cluster.id)
                                    # conMatrix[cluster.id-1][net.gates[subkey].cluster.id-1] += 1
                                    if netKey not in clusterNetSet[cluster.id]:
                                        clusterNetSet[cluster.id].add(netKey)
                                        connectivityUniqueNet[cluster.id].append(net.gates[subkey].cluster.id)
                                        # conMatrixUniqueNet[cluster.id-1][net.gates[subkey].cluster.id-1] += 1
                                        if spaningNetsUnique.get(netKey) == None:
                                            # If the net is not registered as spaning over several clusters, add it.
                                            spaningNetsUnique[netKey] = net
                                            interNets[net.name] = net

    """
    This a very primitive connectivity metric.
    So far, we only compute the total amount of connections between two clusters.
    This means that a same net could be counted multiples times as long as it connects different gates.
    """
    logger.info("Estimating inter-cluster connectivity and exporting it to file inter_cluster_connectivity_{}.csv".format(clustersTotal))
    s = ""
    for key in connectivity:
        s += str(key) + "," + str(len(connectivity[key]))
        s += "\n"
    # print s
    with open("inter_cluster_connectivity_" + str(clustersTotal) + ".csv", 'w') as file:
        file.write(s)



    # if not RAW_INTERCONNECTIONS:
        # logger.info("Processing inter-cluster connectivity matrix and exporting it to inter_cluster_connectivity_matrix_{}.csv".format(clustersTotal))
        # """
        # I want a matrix looking like

        #   1 2 3 4
        # 1 0 8 9 0
        # 2 4 0 4 2
        # 3 5 1 0 3
        # 4 1 4 2 0

        # with the first row and first column being the cluster index, and the inside of the matrix the amount of connections
        # going from the cluster on the column to the cluster on the row (e.g. 8 connections go from 1 to 2 and 4 go from 4 to 1).
        # """
        # s = ""

        # # First row
        # for i in range(clustersTotal):
        #     s += "," + str(i)
        # s += "\n"

        # for i in range(clustersTotal):
        #     s += str(i) # First column
        #     for j in range(clustersTotal):
        #         s+= "," + str(conMatrix[i][j] + 1) # '+1' because we store the matrix index with '-1' to balance the fact that the clusters begin to 1, but the connectivity matric begin to 0.
        #     s += "\n"
        # # print s
        # with open("inter_cluster_connectivity_matrix_" + str(clustersTotal) + ".csv", 'w') as file:
        #     file.write(s)


        # s = ""

        # # First row
        # for i in range(clustersTotal):
        #     s += "," + str(i)
        # s += "\n"

        # for i in range(clustersTotal):
        #     s += str(i) # First column
        #     for j in range(clustersTotal):
        #         s+= "," + str(conMatrixUniqueNet[i][j] + 1) # '+1' because we store the matrix index with '-1' to balance the fact that the clusters begin to 1, but the connectivity matric begin to 0.
        #     s += "\n"
        # # print s
        # with open("inter_cluster_connectivity_matrix_unique_net_" + str(clustersTotal) + ".csv", 'w') as file:
        #     file.write(s)



    logger.info("Processing inter-cluster connectivity without duplicate nets, exporting to inter_cluster_connectivity_unique_nets_{}.csv.".format(clustersTotal))
    s = ""
    for key in connectivityUniqueNet:
        s += str(key) + "," + str(len(connectivityUniqueNet[key]))
        s += "\n"
    # print s
    with open("inter_cluster_connectivity_unique_nets_" + str(clustersTotal) + ".csv", 'w') as file:
        file.write(s)

    #TODO
    # # Compute Rent's terminals, a.k.a. clusters external connectivity
    # for clusterID in connectivityUniqueNet:
    #     terminals = len(connectivityUniqueNet[clusterID])
    #     gateNum = len(clusters[clusterID].gates)
    #     # TODO some clusters appear to have 0 gate. Investigate this, it should not happen.
    #     # This may actually be because of the geometrical clustering getting too fine.
    #     if gateNum > 0:
    #         if gateNum not in self.RentTerminals:
    #             self.RentTerminals[gateNum] = list()
    #         self.RentTerminals[gateNum].append(terminals)




    """
    Intra-cluster connectivity
    """
    logger.info("Computing intra-cluster connectivity")
    connectivityIntra = dict()
    # Dictionary init
    for ck in clusters:
        cluster = clusters[ck]
        connectivityIntra[cluster.id] = []


    for k in nets:
        net = nets[k]
        clusterID = -1 # Begin with '-1' to mark the fact that we are looking at the first gate of the net.
        discardNet = False
        for key in net.gates:
            if net.gates[key].cluster.id != clusterID and clusterID != -1:
                # this gate is not in the same cluster as the previous one. Discard the net.
                discardNet = True
                # print "(" + str(net.name) + ") We found a gate in a different cluster: from " + str(clusterID) + " to " + str(net.gates[key].cluster.id) + "(and net.gates[key] is " + str(net.gates[key]) + ")"
                # print "This concerns the net '" + str(net.name) + "'"
                # TODO break the loop net.gates here
                break
            else:
                clusterID = net.gates[key].cluster.id
                # print "(" + str(net.name) + ") Changing the clusterID to " + str(clusterID)
        if not discardNet and clusterID != -1:
            # Need the != -1 condition because if we reach this branch with clusterID = -1, it means that the net does not have any gate,
            # it means that net.gates is empty, and that *can* happen, it's fine.
            # It's more efficient to check here for clusterID rather than len(net.gates) for every net.
            # print "(" + str(net.name) + ") inside 'if not discardNet:', clusterID = " + str(clusterID)
            connectivityIntra[clusterID].append(net.name)
            intraNets[net.name] = net



    logger.info("Processing intra-cluster connectivity, exporting to intra_cluster_connectivity_{}.csv.".format(clustersTotal))
    s = ""
    for key in connectivityIntra:
        s += str(key) + "," + str(len(connectivityIntra[key]))
        s += "\n"
    # print s
    with open("intra_cluster_connectivity_" + str(clustersTotal) + ".csv", 'w') as file:
        file.write(s)



    totalInterClusterWL = 0
    totalWireLength = 0
    for nk in nets:
        totalWireLength += nets[nk].wl
    for key in spaningNetsUnique:
        totalInterClusterWL += spaningNetsUnique[key].wl
    logger.info("Total inter-cluster wirelength: {}, which is {}% of the total wirelength.".format(locale.format_string("%d", totalInterClusterWL, grouping=True), totalInterClusterWL*100/totalWireLength))
    logger.info("Inter-cluster nets: {}, which is {}% of the total amount of nets.".format(len(spaningNetsUnique), len(spaningNetsUnique) * 100 / len(nets)))


    logger.info("Analyzing clustering effect on net distribution...")
    points = list()
    interNetLength = list()
    intraNetLength = list()
    totalNetLength = list() # Length of all the nets, before clustering
    interNetStr = ""
    intraNetStr = ""
    for net in interNets.values():
        interNetLength.append(net.wl)
        totalNetLength.append(net.wl)
        interNetStr += "{}, {}\n".format(net.name, net.wl)
    for net in intraNets.values():
        intraNetLength.append(net.wl)
        totalNetLength.append(net.wl)
        intraNetStr += "{}, {}\n".format(net.name, net.wl)
    points.append(totalNetLength)
    points.append(interNetLength)
    points.append(intraNetLength)

    logger.info("Total nets length, average: {}, median: {}".format(statistics.mean(totalNetLength), statistics.median(totalNetLength)))
    logger.info("Inter-cluster nets length, average: {}, median: {}".format(statistics.mean(interNetLength), statistics.median(interNetLength)))
    logger.info("Intra-cluster nets length, average: {}, median: {}".format(statistics.mean(intraNetLength), statistics.median(intraNetLength)))

    with open("inter-cluster_nets_wl.out", 'w') as f:
        f.write(interNetStr)
    with open("intra-cluster_nets_wl.out", 'w') as f:
        f.write(intraNetStr)


    filenameInfo = "{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    plt.figure()
    plt.title("Wirelength distribution of all nets, inter-cluster and intra-cluster")
    flierprops = dict(marker='o', markersize=1, linestyle='none')
    plt.boxplot(points, showmeans=True, meanline=True, showfliers=True, flierprops=flierprops)
    # plt.xticks([i+1 for i in range(len(labels))],labels)
    plt.savefig('{}_WL-analysis_boxplot.pdf'.format(filenameInfo))
    # plt.show()


# http://www.geeksforgeeks.org/heap-sort/
# This code is contributed by Mohit Kumra
# To heapify subtree rooted at index i.
# n is size of heap
def heapify(arr, n, i, cloneArr):
    largest = i  # Initialize largest as root
    l = 2 * i + 1     # left = 2*i + 1
    r = 2 * i + 2     # right = 2*i + 2
 
    # See if left child of root exists and is
    # greater than root
    if l < n and arr[i] < arr[l]:
        largest = l
 
    # See if right child of root exists and is
    # greater than root
    if r < n and arr[largest] < arr[r]:
        largest = r
 
    # Change root, if needed
    if largest != i:
        arr[i],arr[largest] = arr[largest],arr[i]  # swap
        cloneArr[i], cloneArr[largest] = cloneArr[largest], cloneArr[i]
 
        # Heapify the root.
        heapify(arr, n, largest, cloneArr)
 
# The main function to sort an array of given size
def heapSort(arr, cloneArr):
    """
    arr is the array containing the nets length.
    cloneArr is the array containing the nets name.
    The sorting is done on arr, but every moving operation has
    to be applied on cloneArr as well. This way, we can keep
    a one to one relationship between the net name and its length.
    """
    n = len(arr)
 
    # Build a maxheap.
    for i in range(n, -1, -1):
        heapify(arr, n, i, cloneArr)
 
    # One by one extract elements
    for i in range(n-1, 0, -1):
        arr[i], arr[0] = arr[0], arr[i]   # swap
        cloneArr[i], cloneArr[0] = cloneArr[0], cloneArr[i]
        heapify(arr, i, 0, cloneArr)




def findClosest(g, gates, gsx, gsy):
    """
    Parameters
    ----------
    g : Gate
        Gate object of which we want to find the closest neighbour *not* in the same cluster.
    gates : dict
        Dictionary of {gate name [str]: Gate object}
    gsx : arr
        Array of gate names sorted by abscica
    gsy : arr
        Array of gate names sorted by ordinate

    Return
    ------
    Gate name [str]
    """



def silouhette(clusters, gates):
    """
    Compute and set the cohesion, separation and silouhette coefficients of gates and clusters passed as parameters.

    Note that clusters with at most one gate will not contribute to the design coefficients or further analysis.

    As of now, the distance computed is simply Manhattan. But this could be set otherwise.
    e.g. it could be the distance of only the gates on the same net or the number of connections to other gates (cohesion: in the same cluster, separation: in other cluster, not only the closest).
    It should be set to reflect the objective of the clustering.

    Parameters
    ----------
    clusters : dict
        dictionary {cluster name [str]: Cluster object}
    gates : dict
        dictionary {gate name [str]: Gate object}
    """

    # # Set cohesion first
    # clusterCohesions = list()
    # for ck in clusters:
    #     cluster = clusters[ck]
    #     gateCohesions = list()
    #     for gk in cluster.gates:
    #         gate = cluster.gates[gk]
    #         for gsk in cluster.gates:
    #             subgate = cluster.gates[gsk]
    #             # Don't compute the distance with the gate itself
    #             distances = list()
    #             if gk != gsk:
    #                 distances.append(manhattanDistance([gate.x, gate.y], [subgate.x, subgate.y]))
    #             if len(distances) > 0:
    #                 cohesion = np.mean(distances)
    #                 gateCohesions.append(cohesion)
    #             else:
    #                 cohesion = 0
    #             gate.setCohesion(cohesion)
    #             # logger.info("Cohesion: {}".format(cohesion))
    #     if len(gateCohesions) > 0:
    #         clusterCohesion = np.mean(gateCohesions)
    #         clusterCohesions.append(clusterCohesion)
    #     else:
    #         clusterCohesion = 0
    #     # logger.info("Cluster {} has a cohesion: {}".format(ck, clusterCohesion))
    # designCohesion = np.mean(clusterCohesions)
    # logger.info("Design cohesion: {}".format(designCohesion))


    # Then separation. The challenge is to find the closest cluster to a gate.
    # One way could be to find the closest gate not in the same cluster. But how to implement it in less than O(n^2)?
    # First, I should have two sorted list of the gates, one based the abscica, the second on the ordinate.
    # Then, for the gate G, I take the two neighbours in both list, and then both neighbours of those four gates.
    # This should get me a neighbouring circle around G. All those neighbouring gates could be added in a Set as to avoid computing duplicates.
    # Let's call this Set SN for Set of Neighbours.
    # If we did not find a suitable gate in this set, we need to expand the boundary.
    # To do so, first duplicate the set. Then for each element of the set, proceed the same way as for G. This might not be the most efficient,
    # but thanks to the structure of the sets, the duplicates will be ignored.
    # Beware not to add G itself to the set.
    # Keep going until the closest gate to G but in a different cluster is found.

    # => KD-tree you genius. You did it un July.


    # # First, create the two sorted arrays.
    # gsxNames = gates.keys()
    # gsyNames = gates.keys()
    # gsxCoord = list()
    # gsyCoord = list()
    # for gk in gates:
    #     gsxCoord.append(gates[gk].x)
    #     gsyCoord.append(gates[gk].y)


    # for ck in clusters:
    #     cluster = clusters[ck]
    #     for gk in cluster.gates:
    #         gate = cluster.gates[gk]
    #         # findClosest(gate, gates, gatesSortedX, gatesSortedY)

    # # Do it quick and dirty for the moment.
    # for n,gk in enumerate(gates):
    #     logger.debug("{}/{}".format(n, len(gates)))
    #     distNeigh = list() # Distance with all the neighbours
    #     distNeighNames = list()
    #     gate = gates[gk]
    #     for gsk in gates:
    #         if gsk != gk:
    #             subgate = gates[gsk]
    #             distNeigh.append(manhattanDistance([gate.x, gate.y], [subgate.x, subgate.y]))
    #             distNeighNames.append(gsk)
    #     heapSort(distNeigh, distNeighNames)
    #     separation = 0
    #     for i, dist in enumerate(distNeigh):
    #         if gates[distNeighNames[i]].cluster.id != gate.cluster.id:
    #             separation = dist
    #             break
    #     gate.separation = separation


    # Cohesion and separation -- connectivity
    clusterCohesions = list()
    clusterSeparations = list()
    clusterSilouhettes = list()
    for ck in clusters:
        cluster = clusters[ck]
        gateCohesions = list()
        gateSeparations = list()
        for gk in cluster.gates:
            gate = cluster.gates[gk]
            cohesion = 0
            separation = 0
            for nk in gate.nets:
                net = gate.nets[nk]
                for gsk in net.gates:
                    subgate = net.gates[gsk]
                    if gsk != gk:
                        if gate.cluster.id != subgate.cluster.id:
                            separation += 1
                        else:
                            cohesion += 1
            gate.setCohesion(cohesion)
            gate.setSeparation(separation)
            gateCohesions.append(cohesion)
            gateSeparations.append(separation)
        cohesion = np.mean(gateCohesions)
        clusterCohesions.append(cohesion)
        cluster.setCohesion(cohesion)
        separation = np.mean(gateSeparations)
        clusterSeparations.append(separation)
        cluster.setSeparation(separation)
        silouhette = (cohesion - separation)/max(cohesion, separation)
        cluster.setSilouhette(silouhette)
        clusterSilouhettes.append(silouhette)
    cohesion = np.mean(clusterCohesions)
    separation = np.mean(clusterSeparations)
    silouhette = np.mean(clusterSilouhettes) # What I want here, is really a distribution of the silouhettes of all clusters. So I guess this 'mean' is alright instead of computing the design silouhette using the canonical formula. We could do both, probably, if needed.
    plt.figure()
    plt.title("Distribution of clusters silouhette")
    plt.boxplot(clusterSilouhettes)
    plt.savefig('clusters_silouhette_boxplot.png')
    # plt.show()




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

    for d in os.listdir(rootDir):
        subdir = os.path.join(rootDir, d)
        if os.path.isdir(subdir):
            os.chdir(subdir)
            logger.info("Working in folder {}".format(subdir))
            logger.info("Extracting clusters")
            clusters = extractClusters(os.path.join(subdir, CLUSTER_F))
            logger.info("Associate clusters and gates")
            clusterGateAssociation(os.path.join(subdir, CLUSTER_GATE_F), clusters, gates)
            clusterConnectivity(clusters, nets)
            silouhette(clusters, gates)