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
        self.cohesion = 0 # average cohesion of all the gates in the cluster
        self.separation = 0 # average separation of all the gates in the cluster
        self.silouhette = 0 # (cohesion - separation)/max(cohesion, separation)

    def addGate(self, gate):
        self.gates[gate.name] = gate

    def setGateArea(self, area):
        self.gateArea = area

    def getGateArea(self):
        return self.gateArea

    def setSilouhette(self, s):
        """
        Should be between -1 and 1
        """
        self.silouhette = s