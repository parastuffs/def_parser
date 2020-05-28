class GatePin:
    """Connection pin of a standard cell.
    
    """
    def __init__(self, pinName, direction=""):
        self.name = pinName # Name of the pin offering this port in the gate.
        self.direction = direction # Direction of the pin: INPUT, OUTPUT, INOUT or FEEDTHRU
        self.ports = [] # List of Port object.
    
    def addPort(self, port):
        self.ports.append(port)

    def setDirection(self, d):
    	self.direction = d
