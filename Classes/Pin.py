class Pin:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0
        self.net = None # Net object
        self.placed = True # Has the pin been placed by the PnR?
        self.approximatedAdditionalLength = 0 # If the net was not placed, need to has this value to the net length.

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def digest(self):
        logger.info("Pin {} at ({}, {})".format(self.name, self.x, self.y))