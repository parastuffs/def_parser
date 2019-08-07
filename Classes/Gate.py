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