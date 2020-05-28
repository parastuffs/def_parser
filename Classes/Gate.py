class Gate:
    def __init__(self, name):
        self.name = name
        self.x = 0 # lower left corner, x
        self.y = 0 # lower left corner, y
        self.width = 0
        self.height = 0
        self.stdCell = "" # Str name of the standard cell.
        self.nets = dict() # key: net name, value: Net object
        self.cluster = None # Cluster object
        self.cohesion = 0 # average distance between the gate and all other gates in the cluster
        self.separation = 0 # average distance btween the gate and all other gates in the nearest cluster
        self.silouhette = 0 # (cohesion - separation)/max(cohesion, separation)

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
        logger.info("Gate {} at ({}, {})".format(self.name, self.x, self.y))

    def getArea(self):
        return self.width * self.height

    def addNet(self, net):
        self.nets[net.name] = net

    def addCluster(self, cluster):
        """
        cluster: Cluster object
        """
        self.cluster = cluster

    def setSilouhette(self, s):
        """
        Should be between -1 and 1
        """
        self.silouhette = s

    def setCohesion(self, c):
        self.cohesion = c

    def setSeparation(self, s):
        self.separation = s