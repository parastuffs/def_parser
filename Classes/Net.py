class Net:
    def __init__(self, name):
        self.name = name
        self.ID = 0
        self.wl = 0
        self.gates = dict()
        self.gatePins = dict() # {gate name : gate pin name}, like in the DEF file. If it's a pin, {pin name : "PIN"}
        self.pins = dict()
        # Gates dispersion inside of the net.
        # A value of '0' means there is eitheir no gate or only one gate in the net.
        self.dispersion = 0
        self.bb = [[0,0],[0,0]] # Net bounding box, [[x_top, y_top], [x_bottom, y_bottom]] in um
        self.hpl = 0 # Hlaf-perimeter length of the bounding box
        self.hpl3d = 0 # HPL after 3D partitioning
        self.is3d = 0 # 1 if 3D net
        self.layer = 0 # 0 or 1, irrelevant if is3d == 1.
        self.metalLayers = set() # Set of metal layers names through which the net is routed.
        self.isRouted = 0 # 1 if the net is exactly routed.

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

    def setdispersion(self, dispersion):
        self.dispersion = dispersion

    def computeHPL(self):
        self.hpl = self.bb[1][0] - self.bb[0][0] + self.bb[1][1] - self.bb[0][1]