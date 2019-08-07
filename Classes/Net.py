class Net:
    def __init__(self, name):
        self.name = name
        self.ID = 0
        self.wl = 0
        self.gates = dict()
        self.pins = dict()
        # Gates dispersion inside of the net.
        # A value of '0' means there is eitheir no gate or only one gate in the net.
        self.dispersion = 0

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