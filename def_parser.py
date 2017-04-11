from __future__ import division # http://stackoverflow.com/questions/1267869/how-can-i-force-division-to-be-floating-point-division-keeps-rounding-down-to-0

class Design:
    def __init__(self):
        self.nets = []        # List of Net objects
        self.gates = []        # List of Gate objects
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
                if inComponents:
                    # Parse the line and extract the cell
                    split = line.split(' ')
                    print split
                    try:
                    	split.index(";\n")
                    except:
	                    gate = Gate(split[1])
	                    """
	                    A cell is always defined on a single line.
	                    On this line, its coordinates are written as
	                    'PLACED ( <abscissa> <ordinate> )'
	                    Hence, we simply need to find the 'PLACE' keyword
	                    and take take the second and third token to extract
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
							design.addGate(gate)
	                    # endOfComponents = True


                if 'END COMPONENTS' in line:
                    inComponents = False
                    endOfComponents = True

                elif 'COMPONENTS' in line:
                    inComponents = True


    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height

    def addGate(self, gate):
        # TODO: check if gate is a Gate object
        self.gates.append(gate) # Append Gate object

class Net:
    def __init__(self, name, netID):
        self.name = name
        self.ID = netID
        self.wl = 0

class Gate:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def digest(self):
    	print "Gate " + self.name + " at (" + str(self.x) + ", " + str(self.y) + ")"


if __name__ == "__main__":
    print "Hello World!"
    design = Design()
    design.ReadArea()
    design.ExtractCells()
    design.Digest()