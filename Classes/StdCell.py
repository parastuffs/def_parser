class StdCell:
    """Standard cell macro
    
    """
    def __init__(self, name):
        self.name = name
        self.width = 0
        self.height = 0
        self.pins = dict() # Dictionary of GatePin objects, {GatePin.name:GatePin}
        self.isMemory = False
    
    def setWidth(self, w):
        self.width=w
        
    def setHeight(self, h):
        self.height = h

    def addPin(self, p):
        self.pins[p.name] = p