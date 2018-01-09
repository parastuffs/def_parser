from __future__ import division # http://stackoverflow.com/questions/1267869/how-can-i-force-division-to-be-floating-point-division-keeps-rounding-down-to-0
from PIL import Image
from math import *
import copy
from sets import Set
import locale
import os
import datetime
import errno
import random
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

RANDOM_SEED = 0 # Set to 0 if no seed is used, otherwise set to seed value.


macros = dict() # Filled inside extractStdCells()
memoryMacros = dict()
# unknownCells = ["SDFQSTKD1", "OAI21D2", "BUFFD4", "OR2XD2", "AOI21D2", "AO22D2", "AO21D2", "AOI22D2", "AOI211D2", "BUFFD8", "OA211D2", "BUFFD16"]
unknownCells = []
deffile = ""

# Amount of clusters wished
clustersTarget = 3000
# Actual amount of clusters
clustersTotal = 0

# clusteringMethod = "Naive_Geometric"

# bb.out file, at least used for SPC.
MEMORY_MACROS = False

# Factor in def file.
# TODO this should be extracted from the .def
# UNITS_DISTANCE_MICRONS = 1000 #SPC,CCX
UNITS_DISTANCE_MICRONS = 10000 #flipr, BoomCore, LDPC

output_dir = ""




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



class Design:
    def __init__(self):
        self.nets = []        # List of Net objects
        self.gates = dict()
        self.pins = dict()        # List of Pin objects
        self.area = 0
        self.width = 0
        self.height = 0
        self.clusters = [] # List of cluster objects
        self.totalWireLength = 0
        self.totalInterClusterWL = 0

    def Digest(self):
        print "Design digest:"
        print "Width: " + str(self.width)
        print "Height: " + str(self.height)
        print "Aspect ratio: " + str(self.width/self.height)
        print "Nets: " + str(len(self.nets))
        print "Total wirelength: " + locale.format("%d", self.totalWireLength, grouping=True)
        print "Gates: " + str(len(self.gates))



    def ReadArea(self):
        print (str("Reading def file ") + deffile)
        with open(deffile, 'r') as f:
            for line in f: # Read the file sequentially
                if 'DIEAREA' in line:
                    area = line.split(' ')
                    self.setWidth(int(area[6])/UNITS_DISTANCE_MICRONS)
                    self.setHeight(int(area[7])/UNITS_DISTANCE_MICRONS)
                    self.setArea()


    #########  ##    ##   ##########   #######   #########  ##         ##         
    ##          ##  ##        ##      ##     ##  ##         ##         ##         
    ##           ####         ##      ##         ##         ##         ##         
    ######        ##          ##      ##         ######     ##         ##         
    ##           ####         ##      ##         ##         ##         ##         
    ##          ##  ##        ##      ##     ##  ##         ##         ##         
    #########  ##    ##       ##       #######   #########  #########  #########  

    def ExtractCells(self):
        print "Reading the def to extract cells."

        inComponents = False
        endOfComponents = False
        unknownCellsCounts = 0

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
                        gate.setStdCell(split[2])
                        # if macros.get(gate.getStdCell()) == None:
                        #     print "Macro not found when looking for cell '" + str(gate.name) + "' of type '" + gate.getStdCell() + "'"
                        if gate.getStdCell() in unknownCells:
                            # StdCell missing from the .lef file. Use default width/height
                            gate.setWidth(0.25)
                            gate.setHeight(0.25)
                            unknownCellsCounts += 1
                        else:
                            gate.setWidth(macros.get(gate.getStdCell())[0]) # Get the width from the macros dictionary.
                            gate.setHeight(macros.get(gate.getStdCell())[1]) # Get the height from the macros dictionary.
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
                            gate.setY(int(split[split.index("PLACED") + 3])/UNITS_DISTANCE_MICRONS)
                        except:
                            try:
                                gate.setY(int(split[split.index("FIXED") + 3])/UNITS_DISTANCE_MICRONS)
                            except:
                                pass
                            else:
                                design.addGate(gate)
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
        totArea = 0
        for key in self.gates:
            totArea += self.gates[key].getArea()
        print "Total area of the gates: " + str(totArea)
        print "Unknown cell encountered: " + str(unknownCellsCounts)
        # exit()


    #########  ##    ##   ##########  ########   ########   ##      ##   #######   
    ##          ##  ##        ##      ##     ##     ##      ###     ##  ##     ##  
    ##           ####         ##      ##     ##     ##      ## ##   ##  ##         
    ######        ##          ##      #######       ##      ##  ##  ##   #######   
    ##           ####         ##      ##            ##      ##   ## ##         ##  
    ##          ##  ##        ##      ##            ##      ##     ###  ##     ##  
    #########  ##    ##       ##      ##         ########   ##      ##   #######   

    def extractPins(self):
        print "Reading the def to extract pins."

        inPins = False
        endOfPins = False

        with open(deffile, 'r') as f:
            line = f.readline()

            while line:

                if 'PINS ' in line:
                    inPins = True

                elif 'END PINS' in line:
                    break

                if inPins and '- ' in line:
                    # Create the pin gate with its name
                    pin = Pin(line.split(' ')[1])
                    nextLine = f.readline()

                    # Skip everything up to the 'PLACED' keyword
                    while not ' PLACED ' in nextLine:
                        nextLine = f.readline()

                    # Now we are at the 'PLACED' line
                    pin.setX(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 2])/UNITS_DISTANCE_MICRONS)
                    pin.setY(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 3])/UNITS_DISTANCE_MICRONS)

                    self.addPin(pin)

                line = f.readline()


    #########  ##    ##   ##########  ##      ##  #########  ##########   #######   
    ##          ##  ##        ##      ###     ##  ##             ##      ##     ##  
    ##           ####         ##      ## ##   ##  ##             ##      ##         
    ######        ##          ##      ##  ##  ##  ######         ##       #######   
    ##           ####         ##      ##   ## ##  ##             ##             ##  
    ##          ##  ##        ##      ##     ###  ##             ##      ##     ##  
    #########  ##    ##       ##      ##      ##  #########      ##       #######   

    def extractNets(self):
        print "Reading the def to extract nets."

        endOfNet = False # end of single net
        endOfNets = False # end of bloc with all the nets
        inNets = False
        instancesPerNetsStr = "" # String containing the content of 'InstancesPerNet.out'.
        netsStr = "" # String containing the content of 'Nets.out'
        wlNetsStr = "NET  NUM_PINS  LENGTH\n" # String containing the content of 'WLnets.out'.
                                              # The 'NUM_PINS' part is the number of gates + the number of pins.
        cellCoordStr = "" # String containing the content of 'CellCoord.out'

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
                        while not 'ROUTED' in netDetails and not ';' in netDetails:

                            if "NONDEFAULTRULE" in netDetails:
                                # Some net use specific rules for spacing and track width.
                                # The keyword for this is 'NONDEFAULTRULE' and occurs
                                # before the 'ROUTED' keyword.
                                # If we find 'NONDEFAULTRULE', skip the line.
                                netDetails = f.readline().strip()
                                continue # ignores the end of the loop and skip to the next iteration.


                            split = netDetails.split(')') # Split the line so that each element is only one pin or gate
                            for gateBlock in split:
                                gateBlockSplit = gateBlock.split() # Split it again to isolate the gate/pin name

                                if len(gateBlockSplit) > 1 and gateBlockSplit[1] == "PIN":
                                    # this a pin, add its name to the net
                                    # '2' bacause we have {(, PIN, <pin_name>}
                                    net.addPin(self.pins.get(gateBlockSplit[2]))
                                elif len(gateBlockSplit) > 1:
                                    # This is a gate, add its name to the net
                                    # '1' because we have {(, <gate_name>, <gate_port>}
                                    gate = self.gates.get(gateBlockSplit[1])
                                    if gate == None:
                                        # This is not a normal situation. Debug.
                                        print "gateblock; " + str(gateBlock)
                                        print "netdetails: " + str(netDetails)
                                        print "Gate we are trying to add: '" + str(gateBlockSplit[1]) + "'"
                                        print "For the net: " + str(net.name)
                                    net.addGate(gate)
                                    gate.addNet(net)
                                    # TODO if gate.name contains '[' or ']', enclose the name between '{}'
                                    instancesPerNetsStr += " " + str(gate.name)

                                    cellCoordStr += str(net.name) + "," + str(gate.name) + "," + \
                                                    str(gate.x) + ', ' + str(gate.y) + "\n"

                            netDetails = f.readline().strip()

                        netLength = 0

                        instancesPerNetsStr += "\n"

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
                                # print netDetailsSplit
                                # print net.name
                                x1 = int(netDetailsSplit[baseIndex+3])
                                y1 = int(netDetailsSplit[baseIndex+4])
                                if netDetailsSplit[baseIndex+6] == '(':
                                    # Some lines only have one set of coordinates (to place a via)
                                    x2 = netDetailsSplit[baseIndex+7]
                                    y2 = netDetailsSplit[baseIndex+8]
                                else:
                                    x2 = x1
                                    y2 = y1
                                    # print netDetailsSplit
                                # TODO What is the third number we sometimes have in the second coordinates bracket?
                                if x2 == "*":
                                    x2 = int(x1)
                                else:
                                    x2 = int(x2)
                                if y2 == "*":
                                    y2 = int(y1)
                                else:
                                    y2 = int(y2)
                                # TODO Ternary expressions?
                                # TODO WEIGHT? cf net clock
                                netLength += (y2 - y1) + (x2 - x1)


                            netDetails = f.readline().strip()
                        netLength = netLength / UNITS_DISTANCE_MICRONS # 10^-4um to um
                        net.setLength(netLength)
                        self.totalWireLength += netLength
                        # print net.name + ": " + str(netLength)

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


    def sortNets(self):
        netLengths = []
        netNames = []
        for net in self.nets:
            netLengths.append(net.wl)
            netNames.append(net.name)

        heapSort(netLengths, netNames)
        filename = deffile.rsplit('.',1)[0].rsplit('/',1)[1] + "_net_wl.csv"
        print "Exporting net lengths to " + filename
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
        global clustersTotal
        print "Clusterizing..."

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
                self.clusters.append(newCluster)
                # print newClusterWidth*newClusterHeight
                clusterListStr += str(newCluster.id) + "\n"

                originX += newClusterWidth
                if originX >= self.width:
                    originX = 0
                    originY += newClusterHeight

        print "Total cluster created: " + str(count)
        clustersTotal = count

        # TODO 'Clusters.out' should be a paramater/argument/global variable?
        print "Dumping Clusters.out"
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)

        # Check for overshoot, clusters outside of design space.
        totalClustersArea = 0
        for cluster in self.clusters:
            # print str(cluster.id) + ", " + str(cluster.origin) + ", width: " + str(cluster.width) + ", height: " + str(cluster.height)
            totalClustersArea += cluster.width * cluster.height
            if cluster.origin[0] + cluster.width > self.width:
                print "WARNING: cluster width out of design bounds."
            if cluster.origin[1] + cluster.height > self.height:
                print "WARNING: cluster height out of design bounds:"
                print "Cluster origin: (" + str(cluster.origin[0]) + ", " + str(cluster.origin[1]) + ")"
                print "Cluster height: " + str(cluster.height)
                print "Design height: " + str(self.height)
                print "Overshoot: " + str(cluster.origin[1] + cluster.height - self.height)
        print "Total cluster area: " + str(totalClustersArea)


        """
        And now, find out wich gates are in each cluster.
        If the origin of a gate is in a cluster, it belongs to that cluster.
        Hence, the leftmost cluster will have more gates.
        """

        checkClusterGates = 0 # Total amount of gates across all clusters. Check value.
        gateKeys = self.gates.keys() # Dump keys from the gates dictionary
        clusterInstancesStr = "" # String of list of cluster instances to dump into ClustersInstances.out
        for cluster in self.clusters:
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

        print "Total amount of place gates in clusters: " + str(checkClusterGates)

        # Dump cluster instances
        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)







    def randomClusterize(self, clustersTarget):

        # First create all the clusters with default values.
        # TODO use the __init__ method of the object Cluster
        for x in range(clustersTarget):
            # TODO What will be the impact of the fact that the cluster has no geometrical meaning, now?
            # What should I put for the coordinates?
            newCluster = Cluster(0, 0, 0, [0, 0], x)
            self.clusters.append(newCluster)











    def clusterizeOneToOne(self):
        """
        Each cluster is one gate.
        """
        print "Clusterizing..."
        global clustersTotal
        clusterListStr = "" # Clusters names list to dump into 'Clusters.out'
        clusterInstancesStr = "" # String of list of cluster instances to dump into ClustersInstances.out

        for i, key in enumerate(self.gates.keys()):
            width = self.gates[key].width
            height = self.gates[key].height
            area = self.gates[key].getArea()
            origin = [self.gates[key].x, self.gates[key].y]
            identifier = i

            cluster = Cluster(width, height, area, origin, identifier)

            cluster.addGate(self.gates[key])

            cluster.setGateArea(area) # Same as the cluster area in this case.

            self.clusters.append(cluster)

            self.gates[key].addCluster(cluster)

            clusterListStr += str(cluster.id) + "\n"
            clusterInstancesStr += str(cluster.id)
            clusterInstancesStr += " " + str(self.gates[key].name) + "\n"

        clustersTotal = len(self.gates)

        # TODO 'Clusters.out' should be a paramater/argument/global variable?
        print "Dumping Clusters.out"
        with open("Clusters.out", 'w') as file:
            file.write(clusterListStr)

        # Dump cluster instances
        with open('ClustersInstances.out', 'w') as file:
            file.write(clusterInstancesStr)

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

        print "Establish connectivity"
        connectivity = dict() # Key: source cluster, values: destination clusters
        connectivityUniqueNet = dict() # Connectivity, but counting only once every net between clusters

        # In this matrix, a 0 means no connection.
        conMatrix = [[0 for x in range(clustersTotal)] for y in range(clustersTotal)]
        conMatrixUniqueNet = [[0 for x in range(clustersTotal)] for y in range(clustersTotal)]
        
        clusterNetSet = dict() # Dictionary of sets.

        spaningNetsUnique = dict() # This dicitonary contains all the nets that span over more than one cluster. The difference with the other dictionaries is that this one contains each net only once. This will be used to compute the total inter-cluster wirelength.

        # TODO Store the files in a seperate folder depending on the clustering.
        clusterAreaOut = "Name Type InstCount Boundary Area\n" # Clusters info to dump into 'ClustersArea.out'

        for cluster in self.clusters:
            connectivity[cluster.id] = []
            connectivityUniqueNet[cluster.id] = []
            clusterNetSet[cluster.id] = Set()
            clusterGateArea = 0 # Cumulated area of the gates in the cluster
            print "Source cluster: " + str(cluster.id)
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
                                        conMatrix[cluster.id-1][net.gates[subkey].cluster.id-1] += 1
                                        if netKey not in clusterNetSet[cluster.id]:
                                            clusterNetSet[cluster.id].add(netKey)
                                            connectivityUniqueNet[cluster.id].append(net.gates[subkey].cluster.id)
                                            conMatrixUniqueNet[cluster.id-1][net.gates[subkey].cluster.id-1] += 1
                                            if spaningNetsUnique.get(netKey) == None:
                                                # If the net is not registered as spaning over several clusters, add it.
                                                spaningNetsUnique[netKey] = net

            # Set the line corresponding to this cluster for the information dumping into clustersArea.out
            clusterAreaOut += str(cluster.id) + " " + "exclusive" + " " + str(len(cluster.gates)) + " " + \
                            "(" + str(cluster.origin[0]) + "," + str(cluster.origin[1]) + ")" + " " + \
                            "(" + str(cluster.origin[0] + cluster.width) + "," + \
                            str(cluster.origin[1] + cluster.height) + ")" + " " + \
                            str(cluster.getGateArea()) + "\n"


        print "Dumping ClustersArea.out"
        with open("ClustersArea.out", 'w') as file:
            file.write(clusterAreaOut)


        """
        This a very primitive connectivity metric.
        So far, we only compute the total amount of connections between two clusters.
        This means that a same net could be counted multiples times as long as it connects different gates.
        """
        print "Estimating inter-cluster connectivity and exporting it to file inter_cluster_connectivity_" + str(clustersTotal) + ".csv"
        s = ""
        for key in connectivity:
            s += str(key) + "," + str(len(connectivity[key]))
            s += "\n"
        # print s
        with open("inter_cluster_connectivity_" + str(clustersTotal) + ".csv", 'w') as file:
            file.write(s)



        if not RAW_INTERCONNECTIONS:
            print "Processing inter-cluster connectivity matrix and exporting it to inter_cluster_connectivity_matrix_" + str(clustersTotal) + ".csv"
            """
            I want a matrix looking like

              1 2 3 4
            1 0 8 9 0
            2 4 0 4 2
            3 5 1 0 3
            4 1 4 2 0

            with the first row and first column being the cluster index, and the inside of the matrix the amount of connections
            going from the cluster on the column to the cluster on the row (e.g. 8 connections go from 1 to 2 and 4 go from 4 to 1).
            """
            s = ""

            # First row
            for i in range(clustersTotal):
                s += "," + str(i)
            s += "\n"

            for i in range(clustersTotal):
                s += str(i) # First column
                for j in range(clustersTotal):
                    s+= "," + str(conMatrix[i][j] + 1) # '+1' because we store the matrix index with '-1' to balance the fact that the clusters begin to 1, but the connectivity matric begin to 0.
                s += "\n"
            # print s
            with open("inter_cluster_connectivity_matrix_" + str(clustersTotal) + ".csv", 'w') as file:
                file.write(s)


            s = ""

            # First row
            for i in range(clustersTotal):
                s += "," + str(i)
            s += "\n"

            for i in range(clustersTotal):
                s += str(i) # First column
                for j in range(clustersTotal):
                    s+= "," + str(conMatrixUniqueNet[i][j] + 1) # '+1' because we store the matrix index with '-1' to balance the fact that the clusters begin to 1, but the connectivity matric begin to 0.
                s += "\n"
            # print s
            with open("inter_cluster_connectivity_matrix_unique_net_" + str(clustersTotal) + ".csv", 'w') as file:
                file.write(s)



        print "Processing inter-cluster connectivity without duplicate nets, exporting to inter_cluster_connectivity_unique_nets_" + str(clustersTotal) + ".csv."
        s = ""
        for key in connectivityUniqueNet:
            s += str(key) + "," + str(len(connectivityUniqueNet[key]))
            s += "\n"
        # print s
        with open("inter_cluster_connectivity_unique_nets_" + str(clustersTotal) + ".csv", 'w') as file:
            file.write(s)





        """
        Intra-cluster connectivity
        """
        print "Computing intra-cluster connectivity"
        connectivityIntra = dict()
        # Dictionary init
        for cluster in self.clusters:
            connectivityIntra[cluster.id] = []


        for net in self.nets:
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



        print "Processing intra-cluster connectivity, exporting to intra_cluster_connectivity_" + str(clustersTotal) + ".csv."
        s = ""
        for key in connectivityIntra:
            s += str(key) + "," + str(len(connectivityIntra[key]))
            s += "\n"
        # print s
        with open("intra_cluster_connectivity_" + str(clustersTotal) + ".csv", 'w') as file:
            file.write(s)




        for key in spaningNetsUnique:
            self.totalInterClusterWL += spaningNetsUnique[key].wl
        print "Total inter-cluster wirelength: " + locale.format("%d", self.totalInterClusterWL, grouping=True) + ", which is " + str(self.totalInterClusterWL*100/self.totalWireLength) + "% of the total wirelength."
        print "Inter-cluster nets: " + str(len(spaningNetsUnique)) + ", which is " + str(len(spaningNetsUnique) * 100 / len(self.nets)) + "% of the total amount of nets."



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
        self.nets.append(net)

    def getAspectRatio(self):
        return self.width/self.height



        ##      ##  #########  ##########  
        ###     ##  ##             ##      
        ## ##   ##  ##             ##      
        ##  ##  ##  ######         ##      
        ##   ## ##  ##             ##      
        ##     ###  ##             ##      
####### ##      ##  #########      ##      
    

class Net:
    def __init__(self, name):
        self.name = name
        self.ID = 0
        self.wl = 0
        self.gates = dict()
        self.pins = dict()

    def addGate(self, gate):
        """
        gate as Gate object
        """
        self.gates[gate.name] = gate

    def addPin(self, pin):
        """
        pin as Pin object
        """
        self.pins[pin.name] = pin

    def setLength(self, length):
        """
        Total wire length, int.
        """
        self.wl = length



         #######      ###     ##########  #########  
        ##           ## ##        ##      ##         
        ##          ##   ##       ##      ##         
        ##   ####  ##     ##      ##      ######     
        ##     ##  #########      ##      ##         
        ##     ##  ##     ##      ##      ##         
####### ########   ##     ##      ##      #########

class Gate:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.stdCell = ""
        self.nets = dict() # key: net name, value: Net object
        self.cluster = None # Cluster object

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def setStdCell(self, stdCell):
        self.stdCell = stdCell

    def getStdCell(self):
        return self.stdCell

    def digest(self):
        print "Gate " + self.name + " at (" + str(self.x) + ", " + str(self.y) + ")"

    def getArea(self):
        return self.width * self.height

    def addNet(self, net):
        self.nets[net.name] = net

    def addCluster(self, cluster):
        """
        cluster: Cluster object
        """
        self.cluster = cluster




        ########   ########   ##      ##  
        ##     ##     ##      ###     ##  
        ##     ##     ##      ## ##   ##  
        #######       ##      ##  ##  ##  
        ##            ##      ##   ## ##  
        ##            ##      ##     ###  
####### ##         ########   ##      ##  

class Pin:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def digest(self):
        print "Pin " + self.name + " at (" + str(self.x) + ", " + str(self.y) + ")"



         #######   ##         ##     ##   #######   ##########  #########  ########   
        ##     ##  ##         ##     ##  ##     ##      ##      ##         ##     ##  
        ##         ##         ##     ##  ##             ##      ##         ##     ##  
        ##         ##         ##     ##   #######       ##      ######     ########   
        ##         ##         ##     ##         ##      ##      ##         ##   ##    
        ##     ##  ##         ##     ##  ##     ##      ##      ##         ##    ##   
#######  #######   #########   #######    #######       ##      #########  ##     ##  

class Cluster:
    def __init__(self, width, height, area, origin, identifier):
        '''
        origin is an array of two coordinates: (x, y)
        '''
        self.id = identifier
        self.area = area
        self.width = width
        self.height = height
        self.origin = origin
        self.gates = dict()
        self.gateArea = 0 # Cumulated area of all the gates in the cluster

    def addGate(self, gate):
        self.gates[gate.name] = gate

    def setGateArea(self, area):
        self.gateArea = area

    def getGateArea(self):
        return self.gateArea



 #######   ##########  ######      #######   #########  ##         ##         
##     ##      ##      ##    ##   ##     ##  ##         ##         ##         
##             ##      ##     ##  ##         ##         ##         ##         
 #######       ##      ##     ##  ##         ######     ##         ##         
       ##      ##      ##     ##  ##         ##         ##         ##         
##     ##      ##      ##    ##   ##     ##  ##         ##         ##         
 #######       ##      ######      #######   #########  #########  #########  

def extractStdCells():
    """
    This function should be given a .lef file from which it will extract information on
    the standard cells of the library.

    Area: the area is given in the first few lines of the definition.
    e.g. 
        SIZE 0.42 BY 0.24 ;
    It begins with the keyword 'SIZE', then the width and height of the cell.
    The size should be in microns.
    """

    # leffile = "/home/para/dev/def_parser/lef/N07_7.5TMint_7.5TM2_M1open.lef"
    lefdir = "/home/para/dev/def_parser/7nm_Jul2017/LEF/"
    # lefdir = "/home/para/dev/def_parser/lef/"
    # lefdir = "/home/para/dev/def_parser/7nm_Jul2017/LEF/45/"
    inMacro = False #Macros begin with "MACRO macro_name" and end with "END macro_name"
    macroName = ""
    areaFound = False
    macroWidth = 0
    macroHeight = 0
    # macros = dict()

    for file in os.listdir(lefdir):
        if file.endswith(".lef"):
            with open(lefdir+file, 'r') as f:
                line = f.readline()
                while line:

                    if 'MACRO' in line:
                        inMacro = True
                        macroName = line.split()[1] # May need to 'line = line.strip("\n")'
                        # print macroName
                        areaFound = False

                    while inMacro and not areaFound:
                        if 'SIZE' in line:
                            macroWidth = float(line.split()[1])
                            # print macroWidth
                            macroHeight = float(line.split()[3])
                            # print macroHeight
                            macros[macroName] = [macroWidth, macroHeight]
                            areaFound = True
                        elif str("END " + macroName) in line:
                            inMacro = False

                        if inMacro and not areaFound:
                            # We are not about to leave the loop
                            # TODO there must be a non dirty way to do this.
                            line = f.readline()

                    line = f.readline()

    # print macros


def extractMemoryMacros(hrows, frows):
    """
    Extract the memory block from bb.out

    BlackBox Type Count GateArea PhysicalArea Porosity TotalArea Width Height Orientation Instances
    """

    bbfile = "/home/para/dev/def_parser/7nm_Jul2017/SPC/bb.out"

    with open(bbfile, 'r') as f:
        lines = f.read().splitlines()

    for i in xrange(0, hrows):
        del lines[0]

    for i in xrange(0, frows):
        del lines[-1]

    # Remove the spaces between the elements on each line
    for i in xrange(0, len(lines)):
        lines[i] = " ".join(lines[i].split())

    i = 0
    while i < len(lines):
        line = lines[i]
        line = line.split()

        # If the line is not empty
        if line:
            instanceCount = int(line[2])
            macros[line[0]] = [float(line[7]), float(line[8])]

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
    print "Hello World!"

    if RANDOM_SEED == 0:
        RANDOM_SEED = random.random()
    random.seed(RANDOM_SEED)
    print "Seed: " + str(RANDOM_SEED)

    # Create the directory for the output.
    rootDir = os.getcwd()
    output_dir = rootDir + "/" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "/"
    print "Working inside " + output_dir

    try:
        os.makedirs(output_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


    extractStdCells()
    if MEMORY_MACROS:
        extractMemoryMacros(14,4)
    # exit()

    # TODO make this into cli parameter
    deffile = "7nm_Jul2017/ldpc.def"
    # deffile = "7nm_Jul2017/BoomCore.def"
    # deffile = "7nm_Jul2017/flipr.def"
    # deffile = "7nm_Jul2017/ldpc_fromGAtech_N07.def"
    # deffile = "7nm_Jul2017/ccx.def"
    # deffile = "7nm_Jul2017/SPC/spc.def" # Don't forget to turn the MEMORY_MACROS on.
    deffile = rootDir + "/" + deffile

    # Change the working directory to the one created above.
    os.chdir(output_dir)

    for clusteringMethod in ["Naive_Geometric", "random"]:
        for clustersTarget in [4, 9, 25, 49, 100, 200, 300, 500, 1000, 2000, 3000]:
        # for clustersTarget in [0]:
            print "Clustering method: " + clusteringMethod
            clustering_dir = output_dir + "/" + deffile.split('/')[-1].split('.')[0] + "_" + clusteringMethod + "_" + str(clustersTarget)

            print "Clustering directory: " + clustering_dir

            try:
                os.makedirs(clustering_dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            # Change the working directory to clustering dir.
            os.chdir(clustering_dir)


            # TODO Why on Earth would I re-read the design as a whole for each
            # clustering method ? It's always the same, it never changes.
            # The only thing that changes is the clustering inside the Design
            # object. It's not critical at the moment, as the clustering is
            # by far the longest part of the execution, but still.

            design = Design()
            design.ReadArea()
            design.ExtractCells()
            # design.Digest()
            design.extractPins()
            # design.Digest()

            design.extractNets()
            design.sortNets()
            design.Digest()

            print design.width * design.height

            if clustersTarget == 0:
                design.clusterizeOneToOne()
            else:
                # Isn't there a cleaner way to call those functions base on clusteringMethod ?
                if clusteringMethod == "Naive_Geometric": 
                    design.clusterize()
                elif clusteringMethod == "random"
                    design.randomClusterize(clustersTarget)
            design.clusterConnectivity()







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
