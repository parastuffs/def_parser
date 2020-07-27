class Pin:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0
        self.net = None # Net object

    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y

    def digest(self):
        logger.info("Pin {} at ({}, {})".format(self.name, self.x, self.y))