class Port:
    """Physical port of standard cell's pin.
    
    """
    def __init__(self, x=0, y=0, width=0, height=0):
        # self.pin = pin # Reference to the Gate_Pin object to which it's linked.
        self.x = x # lower left corner, x
        self.y = y # lower left corner, y
        self.width = width # in microns
        self.height = height # in microns
        self.center = [self.x + (self.width/2), self.y + (self.height/2)]

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def setWidth(self, width):
        self.width = width

    def setHeight(self, height):
        self.height = height
