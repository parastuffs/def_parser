from __future__ import division # http://stackoverflow.com/questions/1267869/how-can-i-force-division-to-be-floating-point-division-keeps-rounding-down-to-0
from PIL import Image
from math import *

macros = dict() # Filled inside extractStdCells()

class Design:
    def __init__(self):
        self.nets = []        # List of Net objects
        self.gates = []        # List of Gate objects
        self.pins = []        # List of Pin objects
        self.area = 0
        self.width = 0
        self.height = 0

    def Digest(self):
        print "Design digest:"
        print "Width: " + str(self.width)
        print "Height: " + str(self.height)
        print "Aspect ratio: " + str(self.width/self.height)
        print "Nets: " + str(len(self.nets))
        print "Gates: " + str(len(self.gates))



    def ReadArea(self):
        print (str("Reading def file"))
        with open("ldpc_5.8.def", 'r') as f:
            for line in f: # Read the file sequentially
                if 'DIEAREA' in line:
                    area = line.split(' ')
                    self.setWidth(int(area[6]))
                    self.setHeight(int(area[7]))
                    self.setArea()

    def ExtractCells(self):
        print "Reading the def to extract cells."

        inComponents = False
        endOfComponents = False

        with open("ldpc_5.8.def", 'r') as f:
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
                            gate.setX(int(split[split.index("PLACED") + 2]))
                        except:
                            try:
                                gate.setX(int(split[split.index("FIXED") + 2]))
                            except:
                                # If this raises an exception, it probably means
                                # we reached the 'END COMPONENTS'
                                pass

                        try:
                            gate.setY(int(split[split.index("PLACED") + 3]))
                        except:
                            try:
                                gate.setY(int(split[split.index("FIXED") + 3]))
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

    def extractPins(self):
        print "Reading the def to extract pins."

        inPins = False
        endOfPins = False

        with open("ldpc_5.8.def", 'r') as f:
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
                    pin.setX(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 2]))
                    pin.setY(int(nextLine.split(' ')[nextLine.split(' ').index("PLACED") + 3]))

                    self.addPin(pin)

                line = f.readline()

    def extractNets(self):
        print "Reading the def to extract nets."

        endOfNet = False # end of single net
        endOfNets = False # end of bloc with all the nets
        inNets = True

        with open("ldpc_5.8.def", 'r') as f:
            line = f.readline()
            while line:

                if 'END NETS' in line:
                    endOfNets = True
                    break

                if ('NETS' in line and not 'SPECIALNETS' in line) or (inNets):
                    inNets = True
                    # print line
                    line = line.strip("\n")

                    if '- ' in line:
                        # new net
                        net = Net(line.split(' ')[1])
                        # print line.split(' ')[1]
                        # Read the next line after the net name,
                        # it should contain the connected cells names.
                        gatesLine = f.readline()
                        while not ' ROUTED ' in gatesLine:
                            split = gatesLine.split(')') # Split the line so that each element is only one pin or gate
                            for gateBlock in split:
                                gateBlockSplit = gateBlock.split(' ') # Split it again to isolate the gate/pin name

                                if len(gateBlockSplit) > 1 and gateBlockSplit[1] == "PIN":
                                    # this a pin, add its name to the net
                                    # '2' bacause we have {(, PIN, <pin_name>}
                                    net.addGate(gateBlockSplit[2])
                                elif len(gateBlockSplit) > 1:
                                    # This is a gate, add its name to the net
                                    # '1' because we have {(, <gate_name>, <gate_port>}
                                    net.addGate(gateBlockSplit[1])

                            gatesLine = f.readline().strip("\n")

                        self.addNet(net)
                    # end if


                line = f.readline()
            # end while


    def clusterize(self):
        # Amount of clusters wished
        clustersTarget = 500

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
        clusters = []
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
                clusters.append(Cluster(newClusterWidth, newClusterHeight, newClusterWidth*newClusterHeight, [originX, originY]))
                # print newClusterWidth*newClusterHeight

                originX += newClusterWidth
                if originX >= self.width:
                    originX = 0
                    originY += newClusterHeight

        print "Total cluster created: " + str(count)

        # Check for overshoot, clusters outside of design space.
        totalClustersArea = 0
        for cluster in clusters:
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




        # Once they are placed, we need to find out which gates are in each cluster.




    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def setArea(self):
        self.area = self.height * self.width

    def addGate(self, gate):
        # TODO: check if gate is a Gate object
        self.gates.append(gate) # Append Gate object

    def addPin(self, pin):
        # TODO: check if pin is a Pin object
        self.pins.append(pin) # Append Pin object

    def addNet(self, net):
        # TODO: check if net is a Net object
        self.nets.append(net)

    def getAspectRatio(self):
        return self.width/self.height

class Net:
    def __init__(self, name):
        self.name = name
        self.ID = 0
        self.wl = 0
        self.gates = []

    def addGate(self, gate):
        """
        gate as str
        """
        self.gates.append(gate)

class Gate:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.stdCell = ""

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


class Cluster:
    def __init__(self, width, height, area, origin):
        '''
        origin is an array of two coordinates: (x, y)
        '''
        self.area = area
        self.width = width
        self.height = height
        self.origin = origin


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

    leffile = "/home/para/dev/def_parser/lef/N07_7.5TMint_7.5TM2_M1open.lef"
    inMacro = False #Macros begin with "MACRO macro_name" and end with "END macro_name"
    macroName = ""
    areaFound = False
    macroWidth = 0
    macroHeight = 0
    # macros = dict()

    with open(leffile, 'r') as f:
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





if __name__ == "__main__":
    print "Hello World!"
    extractStdCells()
    # exit()





    design = Design()
    design.ReadArea()
    design.ExtractCells()
    # design.Digest()
    design.extractPins()
    # design.Digest()

    design.extractNets()
    design.Digest()

    print design.width * design.height

    design.clusterize()






    ########
    ## Image creation
    ########

    imgW = 1000
    imgH = int(imgW * (design.width/design.height))

    data = [0] * ((imgW+1) * (imgH+1))
    print imgW*imgH
    maxPos = 0

    for gate in design.gates:
        position = int(imgW * ((gate.y / design.height) * imgH) + ((gate.x / design.width) * imgW))
        # print "------"
        # print design.height
        # print design.width
        # print gate.y
        # print gate.x
        # print position
        # print gate.y / design.height
        data[position] += 100
        if data[position] > maxPos:
            maxPos = data[position]
        # if data[position] >= 255:
        #     data[position] = 255

    for i in range(len(data)):
        data[i] = int((data[i] * 255.0) / maxPos)


    print "Create the image (" + str(imgW) + ", " + str(imgH) + ")"
    img = Image.new('L', (imgW+1, imgH+1))
    print "Put data"
    img.putdata(data)
    print "save image"
    img.save('out.png')
    # print "show image"
    # img.show()
