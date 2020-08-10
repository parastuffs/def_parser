"""
Usage:
    def_parser.py   [--design=DESIGN] [--clust-meth=METHOD] [--seed=<seed>]
                    [CLUSTER_AMOUNT ...] [--manhattanwl] [--mststwl]
    def_parser.py (--help|-h)
    def_parser.py [--design=DESIGN] (--digest) [--manhattanwl] [--mststwl]

Options:
    --design=DESIGN         Design to cluster. One amongst ldpc, ldpc-2020, flipr, boomcore, spc,
                            spc-2020, spc-bufferless-2020, ccx, ldpc-4x4-serial, ldpc-4x4, smallboom, armm0 or msp430.
    --clust-meth=METHOD     Clustering method to use. One amongst progressive-wl, random,
                            Naive_Geometric, hierarchical-geometric, kmeans-geometric 
                            or kmeans-random. [default: random]
    --seed=<seed>           RNG seed
    CLUSTER_AMOUNT ...      Number of clusters to build. Multiple arguments allowed.
    --manhattanwl           Compute nets wirelength as Manhattan distance.
    --mststwl               Compute nets wirelength as MSTST.
    --digest                Print design's info and exit.
    -h --help               Print this help

Note:
    If you want a one-to-one clustering, set the CLUSTER_AMOUNT to 0.
"""


from __future__ import division # http://stackoverflow.com/questions/1267869/how-can-i-force-division-to-be-floating-point-division-keeps-rounding-down-to-0
from PIL import Image
from math import *
import copy
import locale
import os
import shutil
import datetime
import errno
import random
from docopt import docopt
import logging, logging.config
import numpy as np
import sys
import matplotlib.pyplot as plt
import bst
import statistics
from alive_progress import alive_bar
from Classes.Cluster import *
from Classes.Gate import *
from Classes.Net import *
from Classes.Pin import *
from Classes.Port import *
from Classes.StdCell import *
from Classes.GatePin import *
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

RANDOM_SEED = 0 # Set to 0 if no seed is used, otherwise set to seed value.


macros = dict() # Filled inside extractStdCells()
memoryMacros = dict()
# unknownCells = ["SDFQSTKD1", "OAI21D2", "BUFFD4", "OR2XD2", "AOI21D2", "AO22D2", "AO21D2", "AOI22D2", "AOI211D2", "BUFFD8", "OA211D2", "BUFFD16"]
unknownCells = []
deffile = ""

# Amount of clusters wished
clustersTarget = 3000

# clusteringMethod = "Naive_Geometric"

# bb.out file, at least used for SPC.
MEMORY_MACROS = False

# Factor in def file.
# TODO this should be extracted from the .def
# UNITS_DISTANCE_MICRONS = 1000 #SPC,CCX
UNITS_DISTANCE_MICRONS = 10000 #  flipr, BoomCore, LDPC

output_dir = ""

logger = logging.getLogger('default')

SIG_SKIP = False

# Skipping probability, [0,1]. Probability to skip a net durring the progressive-wl method.
SKIP_PROB = 0.1




 #######     #####    ########   ##########  
##     ##  ##     ##  ##     ##      ##      
##         ##     ##  ##     ##      ##      
 #######   ##     ##  ########       ##      
       ##  ##     ##  ##   ##        ##      
##     ##  ##     ##  ##    ##       ##      
 #######     #####    ##     ##      ## 

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

def EuclideanDistance(a, b):
    """
    Compute the euclidean distance between two points.

    Parameters
    ----------
    a : tuple
        Pair of float (x, y)
    b : tuple
        Pair of float (x, y)

    Returns
    -------
    float
    """
    return sqrt( (a[0] - b[0])**2 + (a[1] - b[1])**2 )




def nearestNeighbour(bst, point, minDist=float('inf')):
    """
    
    Parameter
    ---------
    bst : BST
        Tree in which to find the nearest neighbour
    point : tuple
        Pair or float coordinates
    minDist : float
        Minimum distance found

    Return
    ------
    tuple
        Pair of float coordinates
    """

    candidate = bst.findClosest(point)
    dist = EuclideanDistance(candidate, point)
    if dist < minDist:
        minDist = dist




class Design:
    def __init__(self):
        self.nets = dict()        # Dictionary of Net objects, key: net name
        self.gates = dict()
        self.pins = dict()        # List of Pin objects
        self.area = 0
        self.gatesArea = 0
        self.width = 0
        self.height = 0
        self.clusters = dict() # dictionary of cluster objects. Key: cluster id
        self.totalWireLength = 0
        self.totalInterClusterWL = 0
        # Rent's terminals T (= t G^p)
        # Key: number of gates in the cluster
        # Value: External connectivity of the cluster
        self.RentTerminals = dict()
        self.RentParam = 0
        self.agw = 0 # Average gate width
        self.name = ""

    def Reset(self):
        '''
        Reset all cluster-specific attributes.
        '''
        self.clusters = dict()
        self.totalInterClusterWL = 0

    def Digest(self):
        logger.info("Design digest {}:".format(self.name))
        logger.info("Width: {}".format(self.width))
        logger.info("Height: {}".format(self.height))
        logger.info("Aspect ratio: {}".format(self.width/self.height))
        logger.info("Nets: {}".format(len(self.nets)))
        logger.info("Total wirelength: {}".format(locale.format_string("%d", self.totalWireLength, grouping=True)))
        logger.info("Gates: {}".format(len(self.gates)))
        n = 0
        widths = []
        for key in self.gates:
            n += len(self.gates[key].nets)
            widths.append(self.gates[key].width)
        t = n/len(self.gates)
        self.RentParam = t
        logger.info("Rent's 't' parameter: {}".format(t))
        self.agw = np.mean(widths)
        logger.info("Average gate width: {}".format(self.agw))

        # Gates dispersion
        # logger.info("Compute average gate dispersion")
        # self.GatesDispersion()
        # dispersions = list()
        # nMax = 5 # Number of max values we want to check
        # maxdisp = [0] * nMax
        # maxdispnet = [None] * nMax
        # for k, net in self.nets.items():
        #     if len(net.gates) > 2:
        #         dispersions.append(net.dispersion)
        #         if net.dispersion > min(maxdisp):
        #             maxdisp[maxdisp.index(min(maxdisp))] = net.dispersion
        #             maxdispnet[maxdisp.index(min(maxdisp))] = net
        # logger.info("Average gate dispersion in nets: {}, min: {}, max: {} (computed for nets with 3 or more gates)".format(np.average(dispersions), min(dispersions), max(dispersions)))
        # for i in range(len(maxdisp)):
        #     # logger.info("Max dispersion net gates info, {}:".format(i))
        #     dispx = list()
        #     dispy = list()
        #     for k, gate in maxdispnet[i].gates.items():
        #         # logger.info("x: {}, y: {}".format(gate.x, gate.y))
        #         dispx.append(gate.x)
        #         dispy.append(gate.y)
        #     # Find the max and tell me about its topology
        #     plt.plot(dispx, dispy, 'o')
        #     plt.axis([0, self.width, 0, self.height])
        #     plt.figure()
        # plt.yscale("log")
        # plt.boxplot(dispersions)
        # # plt.show()

        # Manhattan skew
        # TODO

        # Inter-gate distance
        # logger.info("Compute Manhattan inter-gate distance between each pair of connected gates...")
        # self.IntergateDistance()

        logger.info("Getting gate size stats...")
        gateSize = list()
        for g in self.gates.values():
            gateSize.append(g.getArea())
        plt.figure()
        plt.title("Standard cells sizes")
        plt.boxplot(gateSize)
        # plt.show()

        logger.info("Evaluate bounding boxes for every net...")
        self.ComputeBoundingBox()


########   ########   
##     ##  ##     ##  
##     ##  ##     ##  
########   ########   
##     ##  ##     ##  
##     ##  ##     ##  
########   ########   


    def ComputeBoundingBox(self, method=""):
        '''
        Compute the bounding box (BB) for each net in the design.

        For each net, find the lowest x, lowest y, highest x and highest y.
        They don't need to belong to the same gate of whatever.
        They will set the boundaries for the net's BB.

        Once the BB is known, its half-perimeter length (HPL) should give an approximation of the actual wire length.

        In the following, we assume the coordinates origin is in the bottom left.

        Parameters:
        -----------
        method : String
            "Cell" or "Pin"
        '''


        diff = list()
        worstCase = float("inf")
        outStr = ""
        ignoredNets = 0 # count ignored net

        with alive_bar(len(self.nets)) as bar:
            for net in self.nets.values():
                bar()
                botx = float("inf")
                boty = float("inf")
                topx = 0
                topy = 0
                if (len(net.gates) + len(net.pins))> 1:
                    outStr += net.name + " "
                    if net.wl == 0:
                        print(net.name)
                        sys.exit()
                    for gate in net.gates.values():
                        botx = min(botx, gate.x)
                        boty = min(boty, gate.y)
                        topx = max(topx, gate.x+gate.width)
                        topy = max(topy, gate.y+gate.height)
                    for pin in net.pins.values():
                        botx = min(botx, pin.x)
                        boty = min(boty, pin.y)
                        topx = max(topx, pin.x)
                        topy = max(topy, pin.y)
                    net.bb = [[botx, boty], [topx, topy]]
                    net.computeHPL()
                    outStr += str(net.hpl)
                    outStr += " {} {} {} {}\n".format(botx, boty, topx, topy)
                    newDiff = (net.wl - net.hpl)/net.wl
                    diff.append(newDiff)
                    if worstCase > newDiff:
                        worstCase = newDiff
                        worstNet = net
                    # if net.name == "n_43387":
                    #     logger.debug("BB: {}, HPL: {}, wl: {}".format(net.bb, net.hpl, net.wl))
                else:
                    ignoredNets += 1
        logger.info("{} nets were ignored for lack of connection ({}%)".format(ignoredNets, 100*ignoredNets/len(self.nets)))
        logger.info("### Worst net: '{}'".format(worstNet.name))
        logger.info("## WL-HPL skew: {}".format(worstCase))
        logger.info("## Wire length: {}".format(worstNet.wl))
        logger.info("## Wire HPL: {}".format(worstNet.hpl))
        logger.info("## Wire Bounding box: {}".format(worstNet.bb))
        logger.info("## Number of gates: {}".format(len(worstNet.gates)))
        logger.info("#####################")

        plt.figure()
        plt.title("Net (WL - HPL)/WL")
        plt.boxplot(diff)
        # plt.show()
        logger.info("--- BB stats over (WL - HPL)/WL ---")
        logger.info("Mean: {}, median: {}, stdev: {}, min: {}, max: {}".format(statistics.mean(diff), statistics.median(diff), statistics.stdev(diff), min(diff), max(diff)))

        outfile = "hpl.out"
        logger.info("Exporting HPL to {}".format(outfile))
        with open(outfile, 'w') as f:
            f.write(outStr)




        


    def GatesDispersion(self):
        '''
        Compute the gates dispersion in each net.
        '''
        for net in self.nets.values():
            i = 0
            dists = list()
            gatekeys = list(net.gates.keys())
            # print gatekeys
            if len(gatekeys) > 1:
                while i < len(gatekeys):
                    j = i+1
                    while j < len(gatekeys):
                        # Compute the distance between all the gates.
                        dists.append( abs( sqrt( (net.gates[gatekeys[i]].x - net.gates[gatekeys[j]].x)**2 + (net.gates[gatekeys[i]].y - net.gates[gatekeys[j]].y)**2 ) ) )
                        j += 1
                    i += 1
            if len(net.pins) > 0:
                for pin in net.pins:
                    for gate in net.gates.values():
                        dists.append( abs( sqrt( (gate.x - pin.x)**2 + (gate.y - pin.y)**2 ) ) )
            if len(dists) > 0:
                # Compute dispersion
                maxdist = max(dists)
                normaldists = [i/maxdist for i in dists]
                # print normaldists
                pairs = len(gatekeys) * (len(gatekeys)-1) / 2
                dispersion = sum([1/i for i in normaldists])/pairs
                self.nets[kn].setdispersion(dispersion)

    def IntergateDistance(self):
        manDists = list()

        # manDistStr = "Net name, gate A, gate B, Manhattan distance (um), Manhattan distance (agw)\n"
        for kn in self.nets:
            if len(self.nets[kn].gates) > 1:
                kg = list(self.nets[kn].gates.keys())
                for i in range(len(kg)):
                    for j in range(i+1, len(kg)):
                        # logger.debug("i:{}, j:{}".format(i, j))
                        # Manhattan distance is the half-perimeter length of the bounding box containing the two gates.
                        # In other words, the sum of the difference between their two coordinates.
                        manDist = abs(self.nets[kn].gates[kg[i]].x - self.nets[kn].gates[kg[j]].x) + abs(self.nets[kn].gates[kg[i]].y - self.nets[kn].gates[kg[j]].y)
                        manDists.append(manDist)
                        # manDistStr = "{}{}, {}, {}, {}, {}\n".format(manDistStr, str(kn), str(kg[i]), str(kg[j]), str(manDist), str(manDist * self.agw))
        # with open("Manhattan_distances_full_design.csv", 'w') as f:
        #     f.write(manDistStr)

        # manDists.sort()
        # manDistsCumul = np.cumsum(manDists)
        # abscissa = [i for i in range(1,len(manDistsCumul)+1)]

        # plt.plot(abscissa, manDistsCumul)
        # plt.show()

        (plotValues, plotBins, _) = plt.hist([self.agw*i for i in manDists], bins=[i for i in range(1,100)])
        # (plotValues, plotBins, _) = plt.hist([self.agw*i for i in manDists], bins=10)
        plt.xscale("log")
        plt.title("Distribution of inter-gate Manhattan distance\n according to their proportion of average gate width (agw) {}".format(self.agw))
        plt.savefig('{}_intergate_Manhattan_agw_distribution.png'.format(self.name))
        # plt.hist(manDists, bins=10)
        # print("{}, {}".format(plotValues, plotBins))
        plt.figure()
        # print([sum(plotValues[:i+1]) for i in range(len(plotValues))])
        plt.plot(plotBins[1:], [sum(plotValues[:i+1]) for i in range(len(plotValues))], 'o-')
        plt.xscale("log")
        plt.title("Cumulative inter-gate Manhattan distance\n according to their proportion of average gate width (agw) {}".format(self.agw))
        plt.savefig('{}_intergate_Manhattan_agw_cumulative.png'.format(self.name))
            
        # plt.show()







    def ReadArea(self):
        logger.debug("Reading def file {}".format(deffile))
        with open(deffile, 'r') as f:
            for line in f: # Read the file sequentially
                if 'DIEAREA' in line:
                    area = line.split(' ')
                    self.setWidth(int(area[6])/UNITS_DISTANCE_MICRONS)
                    self.setHeight(int(area[7])/UNITS_DISTANCE_MICRONS)
                    self.setArea()

    # def AssignStdCellToGate(self, gate, stdCell):
    #     """ Assign a standard cell to a gate

    #     Copy all the elements in stdCell into gate, but shift all
    #     the coordinates to make them absolute and not relative.

    #     Parameters
    #     ----------
    #     gate: Gate object
    #     stdCell: StdCell object
    #     """



    #########  ##    ##   ##########   #######   #########  ##         ##         
    ##          ##  ##        ##      ##     ##  ##         ##         ##         
    ##           ####         ##      ##         ##         ##         ##         
    ######        ##          ##      ##         ######     ##         ##         
    ##           ####         ##      ##         ##         ##         ##         
    ##          ##  ##        ##      ##     ##  ##         ##         ##         
    #########  ##    ##       ##       #######   #########  #########  #########  

    def ExtractCells(self):
        logger.debug("Reading the def to extract cells.")

        inComponents = False
        endOfComponents = False
        unknownCellsCounts = 0
        cellSizeStr = "cell width height\n"

        with open(deffile, 'r') as f:
            for line in f:
                # TODO: clean to remove the use of break
                # TODO: try to need less try/except
                if endOfComponents:
                    break # Dirty, but I don't care
                if inComponents and not 'END COMPONENTS' in line:
                    # Parse the line and extract the cell
                    split = line.split(' ')
                    # print split
                    try:
                        split.index(";\n")
                    except:
                        gate = Gate(split[1])
                        # AssignStdCellToGate(gate, macros[split[2]])
                        gate.setStdCell(split[2])
                        # if macros.get(gate.getStdCell()) == None:
                        #     print "Macro not found when looking for cell '" + str(gate.name) + "' of type '" + gate.getStdCell() + "'"
                        if gate.getStdCell() in unknownCells:
                            # StdCell missing from the .lef file. Use default width/height
                            gate.setWidth(0.25)
                            gate.setHeight(0.25)
                            unknownCellsCounts += 1
                        else:
                            try:
                                gate.setWidth(macros.get(gate.getStdCell()).width) # Get the width from the macros dictionary.
                                gate.setHeight(macros.get(gate.getStdCell()).height) # Get the height from the macros dictionary.
                            except:
                                logger.error("Could not find the macro '{}' while parsing the line\n{}\nThis macro might be missing from the LEF file. \nExiting.".format(gate.getStdCell(), line))
                                sys.exit()
                        cellSizeStr += "{} {} {}\n".format(gate.name, gate.width, gate.height)
                        """
                        A cell is always defined on a single line.
                        On this line, its coordinates are written as
                        'PLACED ( <abscissa> <ordinate> )'
                        Hence, we simply need to find the 'PLACE' keyword
                        and take the second and third token to extract
                        the coordinates.
                        """
                        # TODO: Is there a way to search the index for two words?
                        # Like index("PLACED" | "FIXED')
                        try:
                            gate.setX(int(split[split.index("PLACED") + 2])/UNITS_DISTANCE_MICRONS)
                        except:
                            try:
                                gate.setX(int(split[split.index("FIXED") + 2])/UNITS_DISTANCE_MICRONS)
                            except:
                                # If this raises an exception, it probably means
                                # we reached the 'END COMPONENTS'
                                pass

                        try:
                            gate.orientation = split[split.index("PLACED") + 5].strip()
                        except:
                            try:
                                gate.orientation = split[split.index("FIXED") + 5].strip()
                            except:
                                # If this raises an exception, it probably means
                                # we reached the 'END COMPONENTS'
                                pass

                        try:
                            gate.setY(int(split[split.index("PLACED") + 3])/UNITS_DISTANCE_MICRONS)
                        except:
                            try:
                                gate.setY(int(split[split.index("FIXED") + 3])/UNITS_DISTANCE_MICRONS)
                            except:
                                pass
                            else:
                                self.addGate(gate)
                        else:
                            self.addGate(gate)
                        # endOfComponents = True


                if 'END COMPONENTS' in line:
                    inComponents = False
                    endOfComponents = True

                elif 'COMPONENTS' in line:
                    inComponents = True

        """
        Compute the total surface of all the gates.
        """
        for key in self.gates:
            self.gatesArea += self.gates[key].getArea()
        logger.debug("Total area of the gates: {} ({}% of total area)".format(self.gatesArea, 100*self.gatesArea/self.area))
        logger.debug("Unknown cell encountered: {}".format(unknownCellsCounts))
        # exit()
        cellSizeStrfname = "CellSizes.out"
        logger.info("Exporting cells dimensions to {}".format(cellSizeStrfname))
        with open(cellSizeStrfname, 'w') as f:
            f.write(cellSizeStr)


    #########  ##    ##   ##########  ########   ########   ##      ##   #######   
    ##          ##  ##        ##      ##     ##     ##      ###     ##  ##     ##  
    ##           ####         ##      ##     ##     ##      ## ##   ##  ##         
    ######        ##          ##      #######       ##      ##  ##  ##   #######   
    ##           ####         ##      ##            ##      ##   ## ##         ##  
    ##          ##  ##        ##      ##            ##      ##     ###  ##     ##  
    #########  ##    ##       ##      ##         ########   ##      ##   #######   

    def extractPins(self):
        logger.debug("Reading the def to extract pins.")

        inPins = False
        endOfPins = False

        with open(deffile, 'r') as f:
            line = f.readline()
            while line:
                nextLine = ""

                if 'PINS ' in line:
                    inPins = True

                elif 'END PINS' in line:
                    break

                if inPins and '- ' in line:
                    # Create the pin gate with its name
                    pin = Pin(line.split(' ')[1])
                    # netIndex = line.split(' ').index("NET")
                    # pin.net = self.nets[line.split(' ')[netIndex + 1]]
                    nextLine = f.readline()

                    # Skip everything up to the 'PLACED' keyword
                    while not ' PLACED ' in nextLine and not '- ' in nextLine and not 'END PINS' in nextLine:
                        nextLine = f.readline()

                    if ' PLACED ' in nextLine:
                        # Now we are at the 'PLACED' line
                        pin.setX(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 2])/UNITS_DISTANCE_MICRONS)
                        pin.setY(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 3])/UNITS_DISTANCE_MICRONS)
                    else:
                        # Could not find a 'placed' instruction for the pin.
                        pin.setX(0)
                        pin.setY(0)

                    self.addPin(pin)

                if '- ' in nextLine or 'END PINS' in nextLine:
                    line = nextLine
                else:
                    line = f.readline()



    #########  ##    ##   ##########  ##      ##  #########  ##########   #######   
    ##          ##  ##        ##      ###     ##  ##             ##      ##     ##  
    ##           ####         ##      ## ##   ##  ##             ##      ##         
    ######        ##          ##      ##  ##  ##  ######         ##       #######   
    ##           ####         ##      ##   ## ##  ##             ##             ##  
    ##          ##  ##        ##      ##     ###  ##             ##      ##     ##  
    #########  ##    ##       ##      ##      ##  #########      ##       #######   

    def extractNets(self, manhattanWireLength=False, mststWireLength=False):
        """
        lefdefref v5.8, p.261.
        """
        logger.debug("Reading the def to extract nets.")

        endOfNet = False # end of single net
        endOfNets = False # end of bloc with all the nets
        inNets = False
        instancesPerNetsStr = "" # String containing the content of 'InstancesPerNet.out'.
        netsStr = "" # String containing the content of 'Nets.out'
        wlNetsStr = "NET  NUM_PINS  LENGTH\n" # String containing the content of 'WLnets.out'.
                                              # The 'NUM_PINS' part is the number of gates + the number of pins.
        cellCoordStr = "" # String containing the content of 'CellCoord.out'

        netCount = 0

        with open(deffile, 'r') as f:
            line = f.readline()
            while line:

                if 'END NETS' in line:
                    endOfNets = True
                    break

                if ('NETS' in line and not 'SPECIALNETS' in line) or (inNets):
                    inNets = True
                    line = line.strip("\n")

                    if '- ' in line:
                        # new net
                        net = Net(line.split(' ')[1])
                        instancesPerNetsStr += str(net.name)
                        netsStr += str(net.name) + "\n"
                        # Read the next line after the net name,
                        # it should contain the connected cells names.
                        netDetails = f.readline()
                        while not 'ROUTED' in netDetails and not ';' in netDetails and not 'PROPERTY' in netDetails and not 'SOURCE' in netDetails:

                            if "NONDEFAULTRULE" in netDetails:
                                # Some net use specific rules for spacing and track width.
                                # The keyword for this is 'NONDEFAULTRULE' and occurs
                                # before the 'ROUTED' keyword.
                                # If we find 'NONDEFAULTRULE', skip the line.
                                netDetails = f.readline().strip()
                                continue # ignores the end of the loop and skip to the next iteration.

                            if "+ USE" in netDetails or "+ WEIGHT" in netDetails:
                                # This is an empty net. Even though it does connect gates,
                                # there is no routing information. Keep its length at 0.
                                netDetails = f.readline().strip()
                                continue


                            split = netDetails.split(')') # Split the line so that each element is only one pin or gate
                            for gateBlock in split:
                                gateBlockSplit = gateBlock.split() # Split it again to isolate the gate/pin name

                                if len(gateBlockSplit) > 1 and gateBlockSplit[1] == "PIN":
                                    # this a pin, add its name to the net
                                    # '2' bacause we have {(, PIN, <pin_name>}
                                    pin = self.pins.get(gateBlockSplit[2])
                                    net.addPin(pin)
                                    pin.net = net
                                    net.gatePins[pin.name] = "PIN"
                                elif len(gateBlockSplit) > 1:
                                    # This is a gate, add its name to the net
                                    # '1' because we have {(, <gate_name>, <gate_port>}
                                    gate = self.gates.get(gateBlockSplit[1])
                                    if gate == None:
                                        # This is not a normal situation. Debug.
                                        logger.error("A gate name has not been recognized in the net description.")
                                        logger.error("gateblock: {}".format(gateBlock))
                                        logger.error("netdetails: {}".format(netDetails))
                                        logger.error("Gate we are trying to add: '{}'".format(gateBlockSplit[1]))
                                        logger.error("For the net: {}".format(net.name))
                                        sys.exit()
                                    net.addGate(gate)
                                    gate.addNet(net)
                                    net.gatePins[gate.name] = gateBlockSplit[2]
                                    # TODO if gate.name contains '[' or ']', enclose the name between '{}'
                                    instancesPerNetsStr += " " + str(gate.name)

                                    cellCoordStr += str(net.name) + "," + str(gate.name) + "," + \
                                                    str(gate.x) + ', ' + str(gate.y) + "\n"

                            netDetails = f.readline().strip()

                        netLength = 0

                        instancesPerNetsStr += "\n"

                        #####
                        # Manhattan distances instead of actual wirelength
                        #####
                        if manhattanWireLength:
                            netCount += 1
                            # logger.debug("Computing Manhattan for net #{}: {}".format(netCount, net.name))
                            cellsToConnect = list(net.gatePins.keys())
                            # Typically want to avoid an unconnected wire or pin on a cell
                            if len(cellsToConnect) > 1:

                                cellsInNet = list(net.gatePins.keys())
                                # logger.debug("cellsToConnect: {}".format(cellsToConnect))
                                # logger.debug("cellsInNet: {}".format(cellsInNet))
                                while len(cellsToConnect) > 0:
                                    minDist = float('inf')
                                    closestCell = ""
                                    # Name of the gate (or pin) we want to connect
                                    gateNameToConnect = cellsToConnect[-1]

                                    # If it's actually a Pin, there is no port or whatnot
                                    if net.gatePins[gateNameToConnect] == "PIN":
                                        # logger.debug("It's a PIN!")
                                        gateToConnectX = self.pins[gateNameToConnect].x
                                        gateToConnectY = self.pins[gateNameToConnect].y

                                        # Compare the pin to all other cells in the net
                                        for gateName in cellsInNet:
                                            # Do not compare the pin to itself
                                            if gateName != gateNameToConnect:
                                                if net.gatePins[gateName] == "PIN":
                                                    dist = abs(gateToConnectX - self.pins[gateName].x) + abs(gateToConnectY - self.pins[gateName].y)
                                                else:
                                                    # Intermediate vars to get the coordinates of the port
                                                    gate = self.gates[gateName]
                                                    stdCellName = gate.stdCell
                                                    gatePin = macros[stdCellName].pins[net.gatePins[gateName]]
                                                    for port in gatePin.ports:
                                                        portCoordinates = gate.absoluteCoordinate(port.center)
                                                        dist = abs(gateToConnectX - portCoordinates[0]) + abs(gateToConnectX - portCoordinates[1])
                                                        if dist < minDist:
                                                            minDist = dist
                                                            closestCell = gateName
                                                if dist < minDist:
                                                    minDist = dist
                                                    closestCell = gateName
                                    else:
                                        # logger.debug("It's not a PIN!")
                                        # Intermediate vars to get the coordinates of the port
                                        gate = self.gates[gateNameToConnect]
                                        stdCellName = gate.stdCell
                                        gatePin = macros[stdCellName].pins[net.gatePins[gateNameToConnect]]
                                        for port in gatePin.ports:
                                            portCoordinates = gate.absoluteCoordinate(port.center)
                                            gateToConnectX = portCoordinates[0]
                                            gateToConnectY = portCoordinates[1]

                                            # Compare the pin to all other cells in the net
                                            for gateName in cellsInNet:
                                                # Do not compare the pin to itself
                                                if gateName != gateNameToConnect:
                                                    if net.gatePins[gateName] == "PIN":
                                                        dist = abs(gateToConnectX - self.pins[gateName].x) + abs(gateToConnectY - self.pins[gateName].y)
                                                    else:
                                                        # Intermediate vars to get the coordinates of the port
                                                        gate = self.gates[gateName]
                                                        stdCellName = gate.stdCell
                                                        gatePin = macros[stdCellName].pins[net.gatePins[gateName]]
                                                        for port in gatePin.ports:
                                                            portCoordinates = gate.absoluteCoordinate(port.center)
                                                            dist = abs(gateToConnectX - portCoordinates[0]) + abs(gateToConnectX - portCoordinates[1])
                                                            if dist < minDist:
                                                                minDist = dist
                                                                closestCell = gateName
                                                    if dist < minDist:
                                                        minDist = dist
                                                        closestCell = gateName


                                    if minDist == float('inf'):
                                        logger.error("Net {} still has infinity wl for cell {}".format(net.name, gateNameToConnect))
                                    netLength += minDist
                                    cellsToConnect.pop()
                                    if closestCell in cellsToConnect:
                                        cellsToConnect.remove(closestCell)

                            # Skip the rest of the details
                            while not ';' in netDetails:
                                netDetails = f.readline().strip()

                        #####
                        # MSTST
                        #####
                        elif mststWireLength:
                            cellsToConnect = list(net.gatePins.keys())

                            points = []
                            for cell in net.gatePins.keys():
                                # If the cell is actually a pin
                                if net.gatePins[cell] == "PIN":
                                    points.append([self.pins[cell].x, self.pins[cell].y])
                                else:
                                    gate = self.gates[cell]
                                    stdCellName = gate.stdCell
                                    gatePin = macros[stdCellName].pins[net.gatePins[cell]]
                                    # Take the first port. It's easier to handle.
                                    port = gatePin.ports[0]
                                    # points.append([port.center[0] + gate.x, port.center[1] + gate.y])
                                    points.append(gate.absoluteCoordinate(port.center))

                            netLength = self.MSTSTwl(points)
                            # Skip the rest of the details
                            while not ';' in netDetails:
                                netDetails = f.readline().strip()
                            if netLength == 0 and len(points) > 1:
                                logger.debug("{}: MSTST length of 0...".format(net.name))
                                logger.debug("\tPoints in net: {}".format(points))
                                logger.debug("\tGates in net: {}".format(cellsToConnect))
                                for cell in cellsToConnect:
                                    gate = self.gates[cell]
                                    stdCellName = gate.stdCell
                                    gatePin = macros[stdCellName].pins[net.gatePins[cell]]
                                    # Take the first port. It's easier to handle.
                                    port = gatePin.ports[0]
                                    logger.debug("\t{} coordinates: {}".format(cell, [gate.x, gate.y]))
                                    logger.debug("\tPort center: {}".format(port.center))
                                    logger.debug("\tOrientation: {}".format(gate.orientation))


                        #####
                        # Actual wirelength
                        #####
                        else:

                            while not ';' in netDetails:
                                # Now, we are looking at the detailed route of the net.
                                # It ends with a single ';' alone on its own line.
                                # On each line, we have:
                                # NEW <routing layer> ( x1 y1 ) ( x2 y2 ) [via(optional]
                                # x2 or y2 can be replaced with '*', meaning the same x1 or y2 is to be used.
                                # 
                                # The only exception should be the first line, which begins with 'ROUTED'



                                if not 'SOURCE' in netDetails and not 'USE' in netDetails and not 'WEIGHT' in netDetails and not 'PROPERTY' in netDetails:
                                    # Skip the lines containing those taboo words.
                                    netDetailsSplit = netDetails.split(' ')
                                    baseIndex = 0 # baseIndex to be shifted in case the line begins with 'ROUTED's
                                    if 'ROUTED' in netDetails:
                                        # First line begins with '+ ROUTED', subsequent ones don't.
                                        # Beware the next lines begin with 'NEW'
                                        baseIndex += 1
                                    if 'TAPER' in netDetails:
                                        # Extra keyword meaning we switch back to the default routing rules.
                                        baseIndex += 1
                                    if 'TAPERRULE' in netDetails:
                                        # Extra keyword meaning we switch to a specific routing rule. 
                                        # The keyword if followed by said rule, so we should add two indexes.
                                        # However the first 'TAPERRULE' has already been taken into account in the previous 'TAPER' branch
                                        baseIndex += 1
                                    # print netDetailsSplit
                                    # print net.name
                                    
                                    # Now check if we have a net extension (see 'routingPoints extValue' in doc)
                                    # We only need to do this for the first coordinates (x1 y1)
                                    if netDetailsSplit[baseIndex+5] != ")":
                                        # There is a net extension. Delete it.
                                        del netDetailsSplit[baseIndex+5]

                                    # Now if there is a MASK statement between two coordinates, trash it.
                                    if "MASK" in netDetailsSplit:
                                        for i in range(len(netDetailsSplit)):
                                            if netDetailsSplit[i] == "MASK":
                                                # "MASK" is always followed by an integer. Trash it alongside. cf. lefdef reference v5.8 p. 261
                                                del netDetailsSplit[i:i+2]
                                                break

                                    try:
                                        x1 = int(netDetailsSplit[baseIndex+3])
                                        y1 = int(netDetailsSplit[baseIndex+4])
                                    except ValueError:
                                        logger.error("Error parsing the line:\n{}\nSplit indexes 3 or 4 is not an integer".format(netDetailsSplit))
                                        sys.exit()
                                    if netDetailsSplit[baseIndex+6] == '(':
                                        # Some lines only have one set of coordinates (to place a via)
                                        x2 = netDetailsSplit[baseIndex+7]
                                        y2 = netDetailsSplit[baseIndex+8]
                                    else:
                                        x2 = x1
                                        y2 = y1
                                        # print netDetailsSplit
                                    # Some lines have up to 3 pairs of coordinates
                                    if len(netDetailsSplit) > baseIndex+10 and netDetailsSplit[baseIndex+10] == '(':
                                        x3 = netDetailsSplit[baseIndex+11]
                                        y3 = netDetailsSplit[baseIndex+12]
                                    else:
                                        x3 = x2
                                        y3 = y2
                                    # TODO What is the third number we sometimes have in the second coordinates bracket?
                                    if x2 == "*":
                                        x2 = int(x1)
                                    else:
                                        x2 = int(x2)
                                    if y2 == "*":
                                        y2 = int(y1)
                                    else:
                                        y2 = int(y2)
                                    if x3 == "*":
                                        x3 = x2
                                    else:
                                        x3 = int(x3)
                                    if y3 == "*":
                                        y3 = y2
                                    else:
                                        y3 = int(y3)
                                    # TODO Ternary expressions?
                                    # TODO WEIGHT? cf net clock
                                    netLength += (abs(y2 - y1) + abs(x2 - x1) + abs(y3 - y2) + abs(x3 - x2))/UNITS_DISTANCE_MICRONS 
                                    # if net.name == "clock_module_0.and_dco_dis5.a":
                                    #     logger.debug("In net clock_module_0.and_dco_dis5.a, netDetailsSplit is: '{}'".format(netDetailsSplit))
                                    #     logger.debug("baseIndex = {}".format(baseIndex))
                                    #     logger.debug("netLength = {}".format(netLength))
                                    #     logger.debug("x1 = {}, y1 = {}, x2 = {}, y2 = {}, x3 = {}, y3 = {}".format(x1, y1, x2, y2, x3, y3))
                                    #     logger.debug("len(netDetailsSplit) = {} and [baseIndex+10] = '{}'".format(len(netDetailsSplit), [baseIndex+10]))


                                netDetails = f.readline().strip()
                        # netLength = netLength / UNITS_DISTANCE_MICRONS # 10^-4um to um
                        net.setLength(netLength)
                        self.totalWireLength += netLength
                        # logger.debug("{}: {}".format(net.name, netLength))

                        self.addNet(net)

                        wlNetsStr += str(net.name) + " " + str(len(net.gates) + len(net.pins)) + " " + str(net.wl) + "\n"
                    # end if


                line = f.readline()
            # end while

        with open("InstancesPerNet.out", 'w') as file:
            file.write(instancesPerNetsStr)

        with open("Nets.out", 'w') as file:
            file.write(netsStr)

        with open("WLnets.out", 'w') as file:
            file.write(wlNetsStr)

        with open("CellCoord.out", 'w') as file:
            file.write(cellCoordStr)


        pinCellsStr = ""
        pinCoordStr = ""
        for pin in self.pins.values():
            pinCoordStr += "{} {} {}\n".format(pin.name, pin.x, pin.y)
            for cell in pin.net.gates.values():
                pinCellsStr += "{}\n".format(cell.name)
        with open("pinCoord.out", 'w') as f:
            f.write(pinCoordStr)
        with open("pinCells.out", 'w') as f:
            f.write(pinCellsStr)

    def MSTSTwl(self, points):
        """
        Minimum Single-Trunk Steiner Tree (MSTST) algorithm to compute the approximate
        wire-length given some points.

        Parameters:
        -----------
        points : List
            List of lists like so:
            [[x1,y1],...,[xn,yn]]

        Return:
        float
            Size of the tree
        """
        # 1. Find the median y coordinate
        trunk = statistics.median([i[1] for i in points])
        wirelength = sum([abs(trunk - i[1]) for i in points])
        wirelength += max([i[0] for i in points]) - min([i[0] for i in points])
        return wirelength

    def sortNets(self):
        netLengths = []
        netNames = []
        for k in self.nets:
            net = self.nets[k]
            netLengths.append(net.wl)
            netNames.append(net.name)

        heapSort(netLengths, netNames)
        filename = deffile.rsplit('.',1)[0].rsplit('/',1)[1] + "_net_wl.csv"
        logger.debug("Exporting net lengths to {}".format(filename))
        s = "Net_name net_wire_length cumulated_wire_length %_of_nets\n"
        cumulatedLength = 0
        for i in range(0, len(netLengths)):
            cumulatedLength += netLengths[i]
            s += str(netNames[i]) + " " + str(netLengths[i]) + " " + str(cumulatedLength) + " " + str((i+1)*100/len(netLengths)) + "\n"
        # print s
        with open(filename, 'w') as file:
            file.write(s)
        # TODO generation du graphe en Python



     #######   ##         ##     ##   #######   ##########  #########  ########   
    ##     ##  ##         ##     ##  ##     ##      ##      ##         ##     ##  
    ##         ##         ##     ##  ##             ##      ##         ##     ##  
    ##         ##         ##     ##   #######       ##      ######     ########   
    ##         ##         ##     ##         ##      ##      ##         ##   ##    
    ##     ##  ##         ##     ##  ##     ##      ##      ##         ##    ##   
     #######   #########   #######    #######       ##      #########  ##     ##  

    def clusterize(self):
        logger.info("Clusterizing...")

        # The first, naive, implementation is to extract clusters from the design with the same aspect ratio.
        # The area of each cluster is the area of the design divided by the amount of clusters.
        clusterArea = self.area / clustersTarget

        # And since the aspect ratio is the width over the height, we find:
        clusterWidth = sqrt(self.getAspectRatio() *  clusterArea)
        clusterHeight = sqrt(clusterArea / self.getAspectRatio() )

        # Once we know the cluster size, we need to place them on the design.
        full = False
        originX = 0
        originY = 0
        count = 0
        clusterListStr = "" # Clusters names list to dump into 'Clusters.out'
        # clusters = []
        while not full:
            if originY >= self.height:
                full = True
            else:
                count += 1
                # Round down.
                newClusterWidth = int(clusterWidth)
                # If what is left on the row after this cluster is not enough for a full cluster to fit, add that space to the cluster being created.
                # This means that the last cluster of each row will be slightly larger (except if they fit exactly in the row), since the actual width is rounded down from the theoretical width.
                if newClusterWidth > self.width - originX - newClusterWidth:
                    newClusterWidth += self.width - originX - newClusterWidth

                newClusterHeight = int(clusterHeight)
                if newClusterHeight > self.height - originY - newClusterHeight:
                    newClusterHeight += self.height - originY -newClusterHeight

                # print "new cluster height: " + str(newClusterHeight)
                # print "new cluster origin: (" + str(originX) + ", " + str(originY) + ")"

                # TODO change the cluster.origin into some sort of point object.
                newCluster = Cluster(newClusterWidth, newClusterHeight, newClusterWidth*newClusterHeight, [originX, originY], count)
                self.clusters[newCluster.id] = newCluster
                # print newClusterWidth*newClusterHeight
                clusterListStr += str(newCluster.id) + "\n"

                originX += newClusterWidth
                if originX >= self.width:
                    originX = 0
                    originY += newClusterHeight

        logger.info("Total cluster created: {}".format(count))

        # TODO 'Clusters.out' should be a paramater/argument/global variable?
        logger.debug("Dumping Clusters.out")
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)

        # Check for overshoot, clusters outside of design space.
        totalClustersArea = 0
        for ck in self.clusters:
            cluster = self.clusters[ck]
            # print str(cluster.id) + ", " + str(cluster.origin) + ", width: " + str(cluster.width) + ", height: " + str(cluster.height)
            totalClustersArea += cluster.width * cluster.height
            if cluster.origin[0] + cluster.width > self.width:
                logger.warning("WARNING: cluster width out of design bounds.")
            if cluster.origin[1] + cluster.height > self.height:
                logger.warning("WARNING: cluster height out of design bounds:")
                logger.warning("Cluster origin: ({}, {})".format(cluster.origin[0], cluster.origin[1]))
                logger.warning("Cluster height: {}".format(cluster.height))
                logger.warning("Design height: {}".format(self.height))
                logger.warning("Overshoot: {}".format(cluster.origin[1] + cluster.height - self.height))
        logger.info("Total cluster area: {}".format(totalClustersArea))
        self.populateGeometricClusters()

        


    def populateGeometricClusters(self):
        """
        And now, find out wich gates are in each cluster.
        If the origin of a gate is in a cluster, it belongs to that cluster.
        Hence, the leftmost cluster will have more gates.
        """

        checkClusterGates = 0 # Total amount of gates across all clusters. Check value.
        gateKeys = list(self.gates.keys()) # Dump keys from the gates dictionary
        clusterInstancesStr = "" # String of list of cluster instances to dump into ClustersInstances.out
        for ck in self.clusters:
            cluster = self.clusters[ck]
            i = 0
            gateKeysNotPlaced = [] # Keys of the gates that have not be placed into a cluster yet.
            clusterGateArea = 0 # Cumulated area of the gates in the cluster
            clusterInstancesStr += str(cluster.id)

            for key in gateKeys:
                # Check if the gate coordinates are below the top right corner of the cluster
                # and above the bottom left corner.
                if self.gates[key].x <= (cluster.origin[0] + cluster.width) and self.gates[key].y <= (cluster.origin[1] + cluster.height) and self.gates[key].x >= cluster.origin[0] and self.gates[key].y >= cluster.origin[1]:
                    cluster.addGate(self.gates[key])
                    # Also add a reference to the cluster inside the Gate object.
                    # This will be useful for the connectivity loop and reducing its time complexity.
                    self.gates[key].addCluster(cluster)
                    # Add the gate area to the total of the cluster:
                    clusterGateArea += self.gates[key].getArea()
                    # TODO if the gate name contains a '[' or ']', put {} around its name.
                    # TODO make sure there is no gate with a space in its name.
                    clusterInstancesStr += " " + str(self.gates[key].name)
                else:
                    gateKeysNotPlaced.append(key)

            gateKeys = list(gateKeysNotPlaced) # Replace the key list with only the keys to the gates that have not been placed.

            checkClusterGates += len(cluster.gates)

            # Set the cluster 'gate area'
            cluster.setGateArea(clusterGateArea)

            clusterInstancesStr += "\n"

        logger.debug("Total amount of place gates in clusters: {} out of {}".format(checkClusterGates, len(self.gates)))

        # Dump cluster instances
        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)



    def splitDesign(self, power, baseCluster):
        """
        @baseCluster: cluster object that needs to be split

        Return: list of Cluster objects

        During the creation of the cluster, simply assign it the ID 0.
        It will be taken care of in the calling function.

        The new cluster is always on the right or bottom.
        When deciding the new dimensions, the base cluster is rounded down
        whilst the new one is rounded up.
        """
        clusterList = []
        if power > 0:
            if power % 2 == 1:
                # Vertical split

                # Create one new cluster and modify the base one.
                # Base becomes left, new right

                widthLeft = floor(baseCluster.width/2)
                heightLeft = baseCluster.height
                areaLeft = widthLeft * heightLeft
                clusterLeft = Cluster(widthLeft, heightLeft, areaLeft, baseCluster.origin, 0)

                splitClusters = self.splitDesign(power - 1, clusterLeft)
                for cluster in splitClusters:
                    clusterList.append(cluster)

                widthRight = baseCluster.width - widthLeft
                heightRight = baseCluster.height
                areaRight = widthRight * heightRight
                originRight = [baseCluster.origin[0] + widthLeft, baseCluster.origin[1]]
                clusterRight = Cluster(widthRight, heightRight, areaRight, originRight, 0)

                splitClusters = self.splitDesign(power - 1, clusterRight)
                for cluster in splitClusters:
                    clusterList.append(cluster)

            elif power % 2 == 0:
                # Horizontal split

                # Base becomes top, new bottom

                widthTop = baseCluster.width
                heightTop = floor(baseCluster.height/2)
                areaTop = widthTop * heightTop
                clusterTop = Cluster(widthTop, heightTop, areaTop, baseCluster.origin, 0)

                splitClusters = self.splitDesign(power - 1, clusterTop)
                for cluster in splitClusters:
                    clusterList.append(cluster)

                widthBot = baseCluster.width
                heightBot = baseCluster.height - heightTop
                areaBot = widthBot * heightBot
                originBot = [baseCluster.origin[0], baseCluster.origin[1] + heightTop]
                clusterBot = Cluster(widthBot, heightBot, areaBot, originBot, 0)

                splitClusters = self.splitDesign(power - 1, clusterBot)
                for cluster in splitClusters:
                    clusterList.append(cluster)

        else:
            clusterList.append(baseCluster)

        return clusterList




##     ##  ########   #########  ########            #######   #########    #####    
##     ##     ##      ##         ##     ##          ##         ##         ##     ##  
##     ##     ##      ##         ##     ##          ##         ##         ##     ##  
#########     ##      ######     ########     ####  ##   ####  ######     ##     ##  
##     ##     ##      ##         ##   ##            ##     ##  ##         ##     ##  
##     ##     ##      ##         ##    ##           ##     ##  ##         ##     ##  
##     ##  ########   #########  ##     ##          ########   #########    #####   

    def hierarchicalGeometricClustering(self, clustersTarget):
        """
        Hierarchical clustering: split the design in two, then each part in two again, etc.
        """
        global SIG_SKIP
        SIG_SKIP = False

        # First, find the closest power of two from clustersTarget.
        if clustersTarget - pow(2,floor(log(clustersTarget, 2))) < pow(2,ceil(log(clustersTarget, 2))) - clustersTarget:
            power = floor(log(clustersTarget, 2))
        else:
            power = ceil(log(clustersTarget, 2))
        clustersAmount = int(pow(2,power))

        logger.info("Creating {} clusters in a hierarchical geometric way.".format(clustersAmount))



        if clustersAmount != clustersTarget:
            # Get current folder name
            clusterDir = os.getcwd().split(os.sep)[-1]
            # Get root path
            clusterDirRoot = os.sep.join(os.getcwd().split(os.sep)[:-1])
            newDir = os.path.join(clusterDirRoot, clusterDir.replace(str(clustersTarget), str(clustersAmount)))

            logger.info("Target ({}) is different from actual amount ({}), moving everything to {}.".format(clustersTarget, clustersAmount, newDir))

            try:
                os.makedirs(newDir)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    SIG_SKIP = True
                    logger.debug("Amount {} already clustered, skipping...".format(clustersAmount))
                    return
                elif e.errno != errno.EEXIST:
                    raise

            for file in os.listdir(os.getcwd()):
                shutil.move(os.path.join(os.getcwd(), file), os.path.join(newDir, file))
            shutil.rmtree(os.getcwd())
            os.chdir(newDir)


        # Create first cluster spanning over the whole design
        baseCluster = Cluster(self.width, self.height, self.area, [0,0], 0)
        clusterList = self.splitDesign(power, baseCluster)

        # Then for each cluster in the list, assign it a new ID and put it
        # inside the dictionary self.clusters

        for i, cluster in enumerate(clusterList):
            cluster.id = i
            self.clusters[i] = cluster


        self.populateGeometricClusters()

        clustersOutStr = ""
        for ck in self.clusters:
            clustersOutStr += str(self.clusters[ck].id) + "\n"

        logger.debug("Dumping Clusters.out")
        with open("Clusters.out", 'w') as file:
            file.write(clustersOutStr)


        # for ck in self.clusters:
        #     cluster = self.clusters[ck]
        #     print cluster.origin
        #     print cluster.width
        #     print cluster.height












########      ###     ##      ##  ######     
##     ##    ## ##    ###     ##  ##    ##   
##     ##   ##   ##   ## ##   ##  ##     ##  
########   ##     ##  ##  ##  ##  ##     ##  
##   ##    #########  ##   ## ##  ##     ##  
##    ##   ##     ##  ##     ###  ##    ##   
##     ##  ##     ##  ##      ##  ######   
    def randomClusterize(self, clustersTarget):

        # TODO use the __init__ method of the object Cluster
        """
        First create all the clusters with default values.
        """
        clusterListStr = "" # Clusters names list to dump into 'Clusters.out'
        for x in range(clustersTarget):
            # TODO What will be the impact of the fact that the cluster has no geometrical meaning, now?
            # What should I put for the coordinates?
            newCluster = Cluster(0, 0, 0, [0, 0], x)
            self.clusters[newCluster.id] = newCluster
            clusterListStr += str(newCluster.id) + "\n"

        logger.debug("Dumping Clusters.out")
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)


        """
        For each gate in the design, choose a random cluster.
        """
        for k in self.gates:
            clusterID = random.choice(list(self.clusters.keys()))
            self.gates[k].addCluster(self.clusters[clusterID])
            self.clusters[clusterID].setGateArea(self.clusters[clusterID].getGateArea() + self.gates[k].getArea())
            self.clusters[clusterID].addGate(self.gates[k])


        """
        Dump the cluster details indide ClustersInstances.out
        """
        clusterInstancesStr = "" # String of list of cluster instances to dump into ClustersInstances.out
        for ck in self.clusters:
            cluster = self.clusters[ck]
            clusterInstancesStr += str(cluster.id)
            for k in cluster.gates:
                clusterInstancesStr += " " + str(cluster.gates[k].name)
            clusterInstancesStr += "\n"
        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)


        """
        Check the size of each cluster and the distribution of gates across them.
        """
        for ck in self.clusters:
            cluster = self.clusters[ck]
            logger.debug("ClusterID: {}, de facto total area: {} ({}%, normal is {}%) with {} gates ({}%)".format(cluster.id, cluster.getGateArea(), 100*cluster.getGateArea()/self.gatesArea, 100/len(self.clusters), len(cluster.gates), 100*len(cluster.gates)/len(self.gates)))

        # TODO export the statistics: area, number of gates






  #####    ##      ##  #########  
##     ##  ###     ##  ##         
##     ##  ## ##   ##  ##         
##     ##  ##  ##  ##  ######     
##     ##  ##   ## ##  ##         
##     ##  ##     ###  ##         
  #####    ##      ##  #########  
    def clusterizeOneToOne(self):
        """
        Each cluster is one gate.
        """
        logger.info("Clusterizing...")
        clusterListStr = "" # Clusters names list to dump into 'Clusters.out'
        clusterInstancesStr = "" # String of list of cluster instances to dump into ClustersInstances.out

        for i, key in enumerate(list(self.gates.keys())):
            width = self.gates[key].width
            height = self.gates[key].height
            area = self.gates[key].getArea()
            origin = [self.gates[key].x, self.gates[key].y]
            identifier = i

            cluster = Cluster(width, height, area, origin, identifier)

            cluster.addGate(self.gates[key])

            cluster.setGateArea(area) # Same as the cluster area in this case.

            self.clusters[cluster.id] = cluster

            self.gates[key].addCluster(cluster)

            clusterListStr += str(cluster.id) + "\n"
            clusterInstancesStr += str(cluster.id)
            clusterInstancesStr += " " + str(self.gates[key].name) + "\n"

        # TODO 'Clusters.out' should be a paramater/argument/global variable?
        logger.debug("Dumping Clusters.out")
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)

        # Dump cluster instances
        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)





########   ########     #####     #######   
##     ##  ##     ##  ##     ##  ##         
##     ##  ##     ##  ##     ##  ##         
#######    ########   ##     ##  ##   ####  
##         ##   ##    ##     ##  ##     ##  
##         ##    ##   ##     ##  ##     ##  
##         ##     ##    #####    ########   


    def progressiveWireLength(self, objective):
        """
        Create clusters until the <objective> wirelength is converted into inracluster wires.
        """
        logger.info("Clusterizing...")

        # Stop point for the clustering, the area disblanced limit has been reached.
        criticalRatioReached = False
        criticalRatio = 0.6
        objective = objective*self.agw



        # Ratio objective/clustersTotal. Must be in increasing order.
        checkpoints = [0.1, 0.12, 0.15, 0.18, 0.2, 0.22, 0.25, 0.28, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9]


        if len(self.clusters) == 0:
            # First, create sorted list of net length and name.
            netLengths = []
            netNames = []
            for k in self.nets:
                net = self.nets[k]
                netLengths.append(net.wl)
                netNames.append(net.name)
            heapSort(netLengths, netNames)


            # Create the basic clusters containing only one gate.
            for i, key in enumerate(list(self.gates.keys())):
                width = self.gates[key].width
                height = self.gates[key].height
                area = self.gates[key].getArea()
                origin = [self.gates[key].x, self.gates[key].y]
                identifier = i

                cluster = Cluster(width, height, area, origin, identifier)

                cluster.addGate(self.gates[key])

                cluster.setGateArea(area) # Same as the cluster area in this case.

                self.clusters[cluster.id] = cluster

                self.gates[key].addCluster(cluster)
        else:
            logger.debug("Reusing the previous step ({} clusters)".format(len(self.clusters)))
            # We ca re-use a previous run.
            # To do so, find all the nets remaining between the clusters.
            # For each cluster, get the gates.
            # For each gate, get the nets.
            # For each net, get the gates and check if they all are in the same cluster.
            netLengths = []
            netNames = []
            for i, cluster in self.clusters.items():
                mainClusterID = cluster.id
                for j, gate in cluster.gates.items():
                    for k, net in gate.nets.items():
                        for l, subgate in net.gates.items():
                            if subgate.cluster.id != mainClusterID:
                                try:
                                    netNames.index(net.name)
                                except ValueError as e:
                                    # The net is not yet in the list
                                    netLengths.append(net.wl)
                                    netNames.append(net.name)
                                break #Stop looking into this net, go on with the next one.
            heapSort(netLengths, netNames)



        minWL = netLengths[0] # Do not use the min() function, I want to fetch the first one. This expects the array to be sorted at first, however.

        while (minWL < objective and len(netNames) > 0 and not criticalRatioReached) :
            if random.uniform(0, 1) > SKIP_PROB:
                # Select the shortest net.
                net = self.nets[netNames[0]]

                # Check that <net> is not entirely contained inside a single cluster.
                # This is not handled the most efficient way, but it sure is easy.
                singleCluster = True
                netClusters = set()
                for k in net.gates:
                    gate = net.gates[k]
                    netClusters.add(gate.cluster.id)
                # TODO move this into the for loop. If the condition is true, break out of the loop.
                if len(netClusters) > 1:
                    singleCluster = False

                # Net already in a single cluster, remove it and consider the next one.
                if singleCluster:
                    del netNames[0]
                    del netLengths[0]
                    continue

                clusterBase = None
                # Merge all the clusters connected by the net.
                for i, key in enumerate(net.gates):
                    gate = net.gates[key]
                    # First gate's cluster will serve as recipient for ther merger
                    if i == 0:
                        # Get the cluster.
                        clusterBase = gate.cluster
                    # If the gate is already in the base cluster, skip it.
                    elif clusterBase.id == gate.cluster.id:
                        continue
                    else:
                        clusterToMerge = gate.cluster
                        # for each gate in the net, identify the corresponding cluster.
                        for keyToMerge in clusterToMerge.gates:
                            gateToMerge = clusterToMerge.gates[keyToMerge]
                        # for each gate in the cluster, add it to the recipient cluster.
                            clusterBase.addGate(gateToMerge)
                        # Change the cluster object reference inside the gate object.
                            gateToMerge.cluster = clusterBase
                        # Change the cluster area.
                        clusterBase.setGateArea(clusterBase.getGateArea() + clusterToMerge.getGateArea())
                        clusterBase.area = clusterBase.getGateArea()
                        # Remove the cluster from the Design list.
                        # If it's not in the dictionary, it simply means it was deleted in a previous step.
                        if clusterToMerge.id in list(self.clusters.keys()):
                            del self.clusters[clusterToMerge.id]
                minWL = netLengths[0]
                # if round(objective/clustersTotal, 2) in checkpoints:
                #     balance = self.checkBalancable(self.clusters)
                #     logger.debug("Checkpoint: {} Current count: {}, objective: {}, balance: {}".format(round(objective/clustersTotal, 2), clustersTotal, objective, balance))
                #     del checkpoints[0]
                #     if balance >= criticalRatio:
                #         criticalRatioReached = True

                # Once added, remove the net from the list.
                # That way, the first net in the list is always the shortest.
                del netNames[0]
                del netLengths[0]
            else:
                # Skip this net.
                # This means put it at the end of the array and remove it from the front.
                netNames.append(netNames[0])
                del netNames[0]
                netLengths.append(netLengths[0])
                del netLengths[0]

        clusterListStr = ""
        clusterInstancesStr = ""

        # Change the cluster IDs so that there is no gap.
        logger.debug("Update clusters ID to remove gaps.")
        clustersTotal = len(self.clusters)
        clusterKeys = list(self.clusters.keys())
        for i, k in enumerate(clusterKeys):
            cluster = self.clusters[k]
            cluster.id = i
            self.clusters[i] = cluster
            clusterListStr += str(cluster.id) + "\n"
            clusterInstancesStr += str(cluster.id)
            for gk in cluster.gates:
                gate = cluster.gates[gk]
                clusterInstancesStr += " " + str(gate.name)
            clusterInstancesStr += "\n"
            # I only want to keep keys [0, clustersTotal - 1]
            if k >= clustersTotal:
                del self.clusters[k]


        logger.debug("Dumping {} clusters in Clusters.out".format(clustersTotal))
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)

        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)



    def checkBalancable(self, clusters):
        """
        Checks whether or not the cluster list is balancable, i.e. that it can be split into two part of
        rougly the same area.

        @clusters: dictionary of Cluster objects
        """
        part1Area = 0
        part2Area = 0

        for ck in clusters:
            i = int(random.uniform(0, 2))
            if i == 0:
                part1Area += clusters[ck].area
            else:
                part2Area += clusters[ck].area
        if float(part1Area) / (part1Area + part2Area) >= float(part2Area) / (part1Area + part2Area):
            return float(part1Area) / (part1Area + part2Area)
        else:
            return float(part2Area) / (part1Area + part2Area)





##   ##    ##       ##  #########     ###     ##      ##   #######   
##  ##     ###     ###  ##           ## ##    ###     ##  ##     ##  
## ##      ## ## ## ##  ##          ##   ##   ## ##   ##  ##         
####       ##  ###  ##  ######     ##     ##  ##  ##  ##   #######   
##  ##     ##       ##  ##         #########  ##   ## ##         ##  
##   ##    ##       ##  ##         ##     ##  ##     ###  ##     ##  
##    ##   ##       ##  #########  ##     ##  ##      ##   #######   

    def kmeans(self, clustersTarget, clusteringMethod):
        """Kmeans clustering.
        The idea is to place regular points in the design that will act as centers of gravity.
        For each of those, we will clusterize the pairs of gates which closest gravity center is that one. This first step actually results in the naive geometric clustering.
        Next, for each cluster, we compute a center of mass from all the gates position, which will become a new center of gravity for the next iteration.
        We then iterate until convergence.

        For the first step, we can have two possibilities:
        1. The target amount of clusters we want to create is the square value of a natural number.
        We thus simply need to place them regularly in the design as such (9 clusters):
        -----------
        | x  x  x |
        | x  x  x |
        | x  x  x |
        -----------

        2. It's not. In that case, there will be an extra gravity line (11 clusters):
        -----------------
        |    x     x    |
        |  x    x    x  |
        |  x    x    x  |
        |  x    x    x  |
        -----------------
        The extra line can have up to (a+1)**2 - a**2 - 1 = 2*a elements.
        We could thus have up to 2*a/a**2 = 2/a clusters that are 'out-of-shape'.



        Parameters
        ----------
        clustersTarget : int
            Amount of clusters we want to create.
        clusteringMethod : str
            Sets the precise method to generate the first centers of gravity,
            "kmeans-geometric" or "kmeans-random".
        """

        logger.info("Creating {} clusters using kmeans.".format(clustersTarget))

        # Number or time we update the center of gravity from the center of mass.
        NRUNS = 300


        if clusteringMethod == "kmeans-geometric":
            # Place the centers of gravity geometricaly.
            centers = list()
            base = sqrt(clustersTarget)
            if base == floor(base):
                # target is a perfect square
                base = int(base)
                for i in range(base):
                    for j in range(base):
                        centers.append(( (0.5+i)*(self.width/base), (0.5+j)*(self.height/base) ))
            else:
                base = int(floor(base))
                if self.width > self.height:
                    # Design is wider than tall, extra column
                    for i in range(base):
                        for j in range(base):
                            centers.append(( (0.5+i)*(self.width/(base+1)), (0.5+j)*(self.height/base) ))
                    # Create extra column of clusters
                    for j in range( clustersTarget - base**2 ):
                        centers.append(( (0.5+base)*(self.width/(base+1)), (0.5+j)*(self.height/(clustersTarget - base**2)) ))
                else:
                    # Design is taller than wide or perfectly square, extra row
                    for i in range(base):
                        for j in range(base+1):
                            centers.append(( (0.5+i)*(self.width/base), (0.5+j)*(self.height/(base+1)) ))
                    # Create extra row of clusters
                    for i in range( clustersTarget - base**2 ):
                        centers.append(( (0.5+i)*(self.width/(clustersTarget - base**2)), (0.5+base)*(self.height/(base+1)) ))
        elif clusteringMethod == "kmeans-random":
            centers = list()
            for i in range(clustersTarget):
                centers.append(( random.uniform(0,self.width), random.uniform(0, self.height) ))

        # print(centers)

        # Run the kmeans algo
        run = 0
        convergence = False
        convCriteria = 1 * self.agw
        centerSkew = list()
        while run < NRUNS and not convergence:
            run += 1
            centerSkewTmp = list()
            # Reset clusters
            self.clusters = dict()

            for i in enumerate(centers):
                cluster =  Cluster(0, 0, 0, [0, 0], i[0])
                self.clusters[cluster.id] = cluster
            
            #######
            # BST #
            #######
            # # Build the BST with all the centers.
            # tree = bst.BST()
            # bst.buildBalancedBST(centers, tree)
            # # Not balanced.
            # # for center in centers:
            # #     bst.insert(center)
            # # sys.exit()

            # # Nearest neighbour
            # for gk in self.gates:
            #     center = tree.nnsearch((self.gates[gk].x, self.gates[gk].y) )
            #     centerIndex = centers.index(center)
            #     self.clusters[centerIndex].addGate(self.gates[gk])
            #     self.gates[gk].addCluster(self.clusters[centerIndex])
            # # sys.exit()

            ##############
            # EXHAUSTIVE #
            ##############

            # Place gates in closest cluster
            minX = 0
            minY = 0
            previousDist = float('inf')
            logger.info("Place gates in the closest cluster...")
            with alive_bar(len(self.gates)) as bar:
                for gk in self.gates:
                    disClosest = float('inf')
                    clustClosest = 0
                    for center in enumerate(centers):
                        disCenter = EuclideanDistance( (self.gates[gk].x, self.gates[gk].y), center[1])
                        if disCenter < disClosest:
                            disClosest = disCenter
                            # The id of the center is the id of the cluster
                            clustClosest = center[0]
                    self.clusters[clustClosest].addGate(self.gates[gk])
                    self.gates[gk].addCluster(self.clusters[clustClosest])
                    bar()

            # Compute center of mass for each cluster
            centerOfMass = list()
            logger.info("Updating center of mass for each cluster...")
            with alive_bar(len(self.clusters)) as bar:
                for ck in self.clusters:
                    sumx = 0
                    sumy = 0
                    if len(self.clusters[ck].gates) > 0:
                        for gk in self.clusters[ck].gates:
                            # This does not need to be optimized. Even if the sum is computed during the cluster formation, we do not gain time. This is fine and more readable.
                            sumx += self.clusters[ck].gates[gk].x
                            sumy += self.clusters[ck].gates[gk].y
                        centerOfMass.append(( sumx/len(self.clusters[ck].gates), sumy/len(self.clusters[ck].gates) ))
                        centerSkewTmp.append(EuclideanDistance(centerOfMass[-1], centers[len(centerOfMass)-1]))
                    else:
                        # If a cluster does not have any gate, get the old value.
                        # This is OK since self.clusters is read in the same order as <centers>.
                        centerOfMass.append( centers[len(centerOfMass)-1] )
                    bar()
            percentile = np.percentile(centerSkewTmp, 95)
            if percentile < convCriteria:
                convergence = True
            centerSkew.append(centerSkewTmp)
            centers = centerOfMass
            logger.debug("Run {}, 95th percentile: {} ({} AGW)".format(run, percentile, percentile/self.agw))
        logger.info("Kmeans runs: {}".format(run))
        plt.figure()
        plt.boxplot(centerSkew)
        plt.savefig('{}_{}_{}_centersSkew_nrun.png'.format(self.name, len(self.clusters), clusteringMethod))
        # plt.show()

        # Set clusters area
        for ck in self.clusters:
            area = 0
            for gk in self.clusters[ck].gates:
                area += self.clusters[ck].gates[gk].getArea()
            self.clusters[ck].setGateArea(area)
            self.clusters[ck].area= area

        # Create ClustersInstances.out
        clusterInstancesStr = ""
        for ck in self.clusters:
            clusterInstancesStr += str(self.clusters[ck].id)
            for gk in self.clusters[ck].gates:
                clusterInstancesStr += " " + str(self.clusters[ck].gates[gk].name)
            clusterInstancesStr += "\n"

        with open("ClustersInstances.out", 'w') as f:
            f.write(clusterInstancesStr)

        # sys.exit()

        # Create output file
        clustersOutStr = ""
        for ck in self.clusters:
            clustersOutStr += str(self.clusters[ck].id) + "\n"

        logger.debug("Dumping Clusters.out")
        with open("Clusters.out", 'w') as file:
            file.write(clustersOutStr)







 #######   ##         ##     ##   #######   ##########   #######     #####    ##      ##  
##     ##  ##         ##     ##  ##     ##      ##      ##     ##  ##     ##  ###     ##  
##         ##         ##     ##  ##             ##      ##         ##     ##  ## ##   ##  
##         ##         ##     ##   #######       ##      ##         ##     ##  ##  ##  ##  
##         ##         ##     ##         ##      ##      ##         ##     ##  ##   ## ##  
##     ##  ##         ##     ##  ##     ##      ##      ##     ##  ##     ##  ##     ###  
 #######   #########   #######    #######       ##       #######     #####    ##      ##  

    def clusterConnectivity(self):
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

        clustersTotal = len(self.clusters)

        for ck in self.clusters:
            cluster = self.clusters[ck]
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


        # Compute Rent's terminals, a.k.a. clusters external connectivity
        for clusterID in connectivityUniqueNet:
            terminals = len(connectivityUniqueNet[clusterID])
            gateNum = len(self.clusters[clusterID].gates)
            # TODO some clusters appear to have 0 gate. Investigate this, it should not happen.
            # This may actually be because of the geometrical clustering getting too fine.
            if gateNum > 0:
                if gateNum not in self.RentTerminals:
                    self.RentTerminals[gateNum] = list()
                self.RentTerminals[gateNum].append(terminals)




        """
        Intra-cluster connectivity
        """
        logger.info("Computing intra-cluster connectivity")
        connectivityIntra = dict()
        # Dictionary init
        for ck in self.clusters:
            cluster = self.clusters[ck]
            connectivityIntra[cluster.id] = []


        for k in self.nets:
            net = self.nets[k]
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



        logger.info("Processing intra-cluster connectivity, exporting to intra_cluster_connectivity_{}.csv.".format(clustersTotal))
        s = ""
        for key in connectivityIntra:
            s += str(key) + "," + str(len(connectivityIntra[key]))
            s += "\n"
        # print s
        with open("intra_cluster_connectivity_" + str(clustersTotal) + ".csv", 'w') as file:
            file.write(s)



        self.totalInterClusterWL = 0
        for key in spaningNetsUnique:
            self.totalInterClusterWL += spaningNetsUnique[key].wl
        logger.info("Total inter-cluster wirelength: {}, which is {}% of the total wirelength.".format(locale.format_string("%d", self.totalInterClusterWL, grouping=True), self.totalInterClusterWL*100/self.totalWireLength))
        logger.info("Inter-cluster nets: {}, which is {}% of the total amount of nets.".format(len(spaningNetsUnique), len(spaningNetsUnique) * 100 / len(self.nets)))


    def clusterArea(self):
        # TODO Store the files in a seperate folder depending on the clustering.
        clusterAreaOut = "Name Type InstCount Boundary Area\n" # Clusters info to dump into 'ClustersArea.out'

        clusterKeys = list(self.clusters.keys())
        for ck in clusterKeys:
            cluster = self.clusters[ck]
            # Set the line corresponding to this cluster for the information dumping into clustersArea.out
            clusterAreaOut += str(cluster.id) + " " + "exclusive" + " " + str(len(cluster.gates)) + " " + \
                            "(" + str(cluster.origin[0]) + "," + str(cluster.origin[1]) + ")" + " " + \
                            "(" + str(cluster.origin[0] + cluster.width) + "," + \
                            str(cluster.origin[1] + cluster.height) + ")" + " " + \
                            str(cluster.getGateArea()) + "\n"


        logger.info("Dumping ClustersArea.out")
        with open("ClustersArea.out", 'w') as file:
            file.write(clusterAreaOut)


    def RentStats(self, outFile):
        '''
        Export all Rent stats to outFile.
        Not ordered at the moment
        '''
        outStr = "gate count, terminals\n"

        for key in self.RentTerminals:
            if key != len(self.gates):
                outStr += str(key)
                for count in self.RentTerminals[key]:
                    outStr += ", " + str(count)
                outStr += "\n"

        logger.debug("Dumping {}".format(outFile))
        with open(outFile, 'w') as file:
            file.write(outStr)        



    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def setArea(self):
        self.area = self.height * self.width

    def addGate(self, gate):
        # TODO: check if gate is a Gate object
        self.gates[gate.name] = gate

    def addPin(self, pin):
        # TODO: check if pin is a Pin object
        self.pins[pin.name] = pin

    def addNet(self, net):
        # TODO: check if net is a Net object
        self.nets[net.name] = net

    def getAspectRatio(self):
        return self.width/self.height



 #######   ##########  ######      #######   #########  ##         ##         
##     ##      ##      ##    ##   ##     ##  ##         ##         ##         
##             ##      ##     ##  ##         ##         ##         ##         
 #######       ##      ##     ##  ##         ######     ##         ##         
       ##      ##      ##     ##  ##         ##         ##         ##         
##     ##      ##      ##    ##   ##     ##  ##         ##         ##         
 #######       ##      ######      #######   #########  #########  #########  

def extractStdCells(tech, memory=False):
    """
    @tech: 7nm|45nm|gsclib045

    Area: the area is given in the first few lines of the definition.
    e.g. 
        SIZE 0.42 BY 0.24 ;
    It begins with the keyword 'SIZE', then the width and height of the cell.
    The size should be in microns.
    """

    # leffile = "/home/para/dev/def_parser/lef/N07_7.5TMint_7.5TM2_M1open.lef"
    # lefdir = "/home/para/dev/def_parser/lef/"
    if tech == "7nm":
        lefdir = "/home/para/dev/def_parser/7nm_Jul2017/LEF/" # flipr, boomcore, ldpc
        if memory == True:
            lefdir = "/home/para/dev/def_parser/spc_NoBuff/mem"
    elif tech == "45nm":
        lefdir = "/home/para/dev/def_parser/7nm_Jul2017/LEF/45/" # ccx, spc
    elif tech == "gsclib045":
        lefdir = "/home/para/dev/def_parser/SmallBOOM_CDN45/" # smallboom
    elif tech == "osu018":
        lefdir = "/home/para/dev/def_parser/msp430/" # msp430
    else:
        logger.error("Technology {} not supported. Exiting.".format(tech))


    
    inMacro = False #Macros begin with "MACRO macro_name" and end with "END macro_name"
    macroName = ""
    areaFound = False
    macroWidth = 0
    macroHeight = 0
    # macros = dict()
    pin = None
    newPort = False
    inPin = False

    # TODO cleanup
    # Useless:
    # - areaFound

    for file in os.listdir(lefdir):
        if file.endswith(".lef"):
            with open(os.path.join(lefdir,file), 'r') as f:
                logger.debug("Opening {}".format(os.path.join(lefdir,file)))
                line = f.readline()
                while line:

                    if 'MACRO' in line and len(line.split()) == 2 and not 'SITE' in line:
                        inMacro = True
                        macroName = line.split()[1] # May need to 'line = line.strip("\n")'
                        # print macroName
                        areaFound = False
                        macro = StdCell(macroName)
                        # logger.debug("parsing macro '{}'".format(macroName))

                    while inMacro:
                        # logger.debug(line)
                        if 'SIZE' in line:
                            macroWidth = float(line.split()[1])
                            # print macroWidth
                            macro.setWidth(macroWidth)
                            macroHeight = float(line.split()[3])
                            # print macroHeight
                            macro.setHeight(macroHeight)
                            # macros[macroName] = [macroWidth, macroHeight]
                            macros[macroName] = macro
                            areaFound = True
                        elif 'PIN ' in line:
                            pin = GatePin(line.split()[1])
                            inPin = True
                        elif inPin and "END {}".format(pin.name) in line:
                            # End of the PIN statement
                            # logger.debug("Add pin to macro")
                            macro.addPin(pin)
                            inPin = False
                        elif 'DIRECTION' in line:
                            pin.setDirection(line.split()[1])
                        elif 'PORT' in line:
                            newPort = True
                        elif inPin and 'RECT' in line:
                            # Geometry of a PORT from a PIN
                            # Needs to make sure it's inside a PIN block,
                            # otherwise we might catch an OBS block (Macro Obstruction Statement).
                            port = None
                            if 'MASK' in line:
                                # Some lines are as such: RECT MASK 2 0.2190 0.0540 0.2430 0.0740 ;
                                port = Port(x=float(line.split()[3]), y=float(line.split()[4]), width=float(line.split()[5])-float(line.split()[3]), height=float(line.split()[6])-float(line.split()[4]))
                            else:
                                # But most lines are like: RECT 0.1770 0.1200 0.2010 0.1360 ;
                                port = Port(x=float(line.split()[1]), y=float(line.split()[2]), width=float(line.split()[3])-float(line.split()[1]), height=float(line.split()[4])-float(line.split()[2]))
                            pin.addPort(port)

                        elif "END" in line and macroName in line:
                            inMacro = False

                        # if inMacro and not areaFound:
                        # if inMacro and not areaFound:
                            # We are not about to leave the loop
                            # TODO there must be a non dirty way to do this.
                            # line = f.readline()
                        line = f.readline()

                    line = f.readline()

    # print macros
    # TODO check that the StdCell objects in the macro dictionary are still there. Check that they are not nulled after exiting the loop.
    # for macro in macros.values():
    #     logger.debug("macro: {}".format(macro.name))
    #     for pin in macro.pins.values():
    #         logger.debug("pin: {}".format(pin.name))
    #         for port in pin.ports:
    #             logger.debug("PORT at ({}, {})".format(port.x, port.y))


def extractMemoryMacros(hrows, frows):
    """
    Extract the memory block from bb.out

    BlackBox Type Count GateArea PhysicalArea Porosity TotalArea Width Height Orientation Instances
    """

    bbfile = "/home/para/dev/def_parser/7nm_Jul2017/SPC/bb.out"

    with open(bbfile, 'r') as f:
        lines = f.read().splitlines()

    for i in range(0, hrows):
        del lines[0]

    for i in range(0, frows):
        del lines[-1]

    # Remove the spaces between the elements on each line
    for i in range(0, len(lines)):
        lines[i] = " ".join(lines[i].split())

    i = 0
    while i < len(lines):
        line = lines[i]
        line = line.split()

        # If the line is not empty
        if line:
            instanceCount = int(line[2])
            macro = StdCell(line[0])
            macro.setWidth(float(line[7]))
            macro.setHeight(float(line[8]))

            macros[macro.name] = macro
            # logger.debug("Adding memory macro {}".format(line[0]))

            # Skip the line containing only an instance name
            for k in range(instanceCount-1):
                #skip
                i += 1
        i += 1






        ##       ##     ###     ########   ##      ##          
        ###     ###    ## ##       ##      ###     ##          
        ## ## ## ##   ##   ##      ##      ## ##   ##          
        ##  ###  ##  ##     ##     ##      ##  ##  ##          
        ##       ##  #########     ##      ##   ## ##          
        ##       ##  ##     ##     ##      ##     ###          
####### ##       ##  ##     ##  ########   ##      ##  ####### 


if __name__ == "__main__":


    stdCellsTech = ""
    clusteringMethod = "random"
    clustersTargets = []
    DIGESTONLY = False
    manhattanWireLength = False
    mststWireLength = False

    args = docopt(__doc__)
    if args["--design"] == "ldpc":
        deffile = "7nm_Jul2017/ldpc.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    if args["--design"] == "ldpc-2020":
        deffile = "LDPC-2020/ldpc_routed.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "flipr":
        deffile = "7nm_Jul2017/flipr.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "boomcore":
        deffile = "7nm_Jul2017/BoomCore.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "ldpc-4x4-serial":
        deffile = "ldpc_4x4_serial.def/ldpc-4x4-serial.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "ldpc-4x4":
        deffile = "ldpc_4x4/ldpc-4x4.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "ccx":
        deffile = "7nm_Jul2017/ccx.def"
        MEMORY_MACROS = False
        UNITS_DISTANCE_MICRONS = 1000
        stdCellsTech = "45nm"
    elif args["--design"] == "spc":
        deffile = "7nm_Jul2017/SPC/spc.def"
        MEMORY_MACROS = True
        UNITS_DISTANCE_MICRONS = 1000
        stdCellsTech = "45nm"
    elif args["--design"] == "spc-2020":
        deffile = "spc_NoBuff/spc.def"
        MEMORY_MACROS = True
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "spc-bufferless-2020":
        deffile = "spc_NoBuff/spc_NoBuff.def"
        MEMORY_MACROS = True
        UNITS_DISTANCE_MICRONS = 10000
        stdCellsTech = "7nm"
    elif args["--design"] == "smallboom":
        deffile = "SmallBOOM_CDN45/SmallBOOM.def"
        UNITS_DISTANCE_MICRONS = 2000
        stdCellsTech = "gsclib045"
    elif args["--design"] == "armm0":
        deffile = "armM0/ArmM0_all.def"
        UNITS_DISTANCE_MICRONS = 2000
        stdCellsTech = "gsclib045"
    elif args["--design"] == "msp430":
        deffile = "msp430/openMSP430.def"
        UNITS_DISTANCE_MICRONS = 100
        stdCellsTech = "osu018"
    print(stdCellsTech)

    if args["--clust-meth"]:
        clusteringMethod = args["--clust-meth"]

    # TODO add a list of legit methods. If the cli argument is not among them, throw an error and exit.

    if args["CLUSTER_AMOUNT"]:
        for n in args["CLUSTER_AMOUNT"]:
            clustersTargets.append(int(n))
    else:
        clustersTargets = [9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000]

    if args["--seed"]:
        RANDOM_SEED = args["--seed"]
    else:
        RANDOM_SEED = random.random()
    random.seed(RANDOM_SEED)

    if args["--digest"]:
        DIGESTONLY = True
        clusteringMethod = "digest"

    if args["--manhattanwl"]:
        manhattanWireLength = True


    if args["--mststwl"]:
        mststWireLength = True

    if clustersTargets == 0:
        clusteringMethod = "OneToOne"


    # Create the directory for the output.
    rootDir = os.getcwd()
    output_dir = rootDir + "/" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + args["--design"] + "_" + str(clusteringMethod) + "/"

    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    # Load base config from conf file.
    logging.config.fileConfig('log.conf')
    # Load logger from config
    logger = logging.getLogger('default')
    # Create new file handler
    fh = logging.FileHandler(os.path.join(output_dir, 'def_parser_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.log'))
    # Set a format for the file handler
    fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    # Add the handler to the logger
    logger.addHandler(fh)

    logger.debug(args)
    
    logger.info("Working inside {}".format(output_dir))

    logger.info("Seed: {}".format(RANDOM_SEED))


    extractStdCells(stdCellsTech)
    if MEMORY_MACROS:
        # Old SPC, not supported anymore.
    #     extractMemoryMacros(14,4)
        extractStdCells(stdCellsTech, True)
    # exit()

    deffile = os.path.join(rootDir, deffile)

    # Change the working directory to the one created above.
    os.chdir(output_dir)


    design = Design()
    design.name = args["--design"]
    design.ReadArea()
    design.ExtractCells()
    # design.Digest()
    design.extractPins()
    # design.Digest()

    design.extractNets(manhattanWireLength, mststWireLength)
    design.sortNets()
    design.Digest()
    if DIGESTONLY:
        sys.exit()

    # for clustersTarget in [500]:
    # for clustersTarget in [4, 9, 25, 49, 100, 200, 300, 500, 1000, 2000, 3000]:
    # for clustersTarget in [9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000]:
    # TODO sort clustersTargets (reversed for progressive-wl)
    for clustersTarget in clustersTargets:
        logger.info("Clustering method: {}".format(clusteringMethod))
        clustering_dir = os.path.join(output_dir, deffile.split('/')[-1].split('.')[0] + "_" + clusteringMethod + "_" + str(clustersTarget))

        logger.info("Clustering directory: {}".format(clustering_dir))

        try:
            os.makedirs(clustering_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Change the working directory to clustering dir.
        os.chdir(clustering_dir)

        if clusteringMethod != "progressive-wl":
            design.Reset()

        logger.debug(design.width * design.height)

        if clustersTarget == 0:
            design.clusterizeOneToOne()
        else:
            # Isn't there a cleaner way to call those functions base on clusteringMethod ?
            if clusteringMethod == "Naive_Geometric": 
                design.clusterize()
                design.clusterConnectivity()
            elif clusteringMethod == "random":
                design.randomClusterize(clustersTarget)
                design.clusterConnectivity()
            elif clusteringMethod == "progressive-wl":
                design.progressiveWireLength(clustersTarget)
                design.clusterConnectivity()
            elif clusteringMethod == "hierarchical-geometric":
                design.hierarchicalGeometricClustering(clustersTarget)
                if not SIG_SKIP:
                    design.clusterConnectivity()
            elif "kmeans" in clusteringMethod:
                design.kmeans(clustersTarget, clusteringMethod)
                design.clusterConnectivity()
        design.clusterArea()

    os.chdir(output_dir)
    design.RentStats("RentStats.csv")

    logger.info("End of all.")






    ########
    ## Image creation
    ########

    # imgW = 1000
    # imgH = int(imgW * (design.width/design.height))

    # data = [0] * ((imgW+1) * (imgH+1))
    # print imgW*imgH
    # maxPos = 0

    # for key in design.gates:
    #     position = int(imgW * ((design.gates[key].y / design.height) * imgH) + ((design.gates[key].x / design.width) * imgW))
    #     # print "------"
    #     # print design.height
    #     # print design.width
    #     # print position
    #     data[position] += 100
    #     if data[position] > maxPos:
    #         maxPos = data[position]
    #     # if data[position] >= 255:
    #     #     data[position] = 255

    # for i in range(len(data)):
    #     data[i] = int((data[i] * 255.0) / maxPos)


    # print "Create the image (" + str(imgW) + ", " + str(imgH) + ")"
    # img = Image.new('L', (imgW+1, imgH+1))
    # print "Put data"
    # img.putdata(data)
    # print "save image"
    # img.save('out.png')
    # # print "show image"
    # # img.show()
