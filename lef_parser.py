import numpy as np

class Macro:
    def __init__(self, name):
        self.name = name
        self.pins = dict() # dictionary of Pin objects. Key: name of the pin.
        self.width = 0
        self.height = 0

    def numberPins(self):
        return len(self.pins)

    def addPin(self, pin):
        '''
        pin: Pin object
        '''
        self.pins[pin.name] = pin

    def setWidth(self, w):
        self.width = w

    def setHeight(self, h):
        self.height = h


class Pin:
    def __init__(self,name):
        self.name = name


def parse_lef(file):
    pinBlock = False # True if we are in a PIN block.
    macroBlock = False # True if we are in a MACRO block.

    macros = dict() # Dictionary of Macro objects. Key: macro name.

    with open(file, 'r') as f:
        line = f.readline()
        while line:
            line = line.strip()
            # print line
            if 'PIN' in line:
                pin = Pin(line.split()[1]) # Create a Pin object. The name of the pin is the second word in the line 'PIN ...'
                macro.addPin(pin)
                # print "Added the pin '"+str(pin.name)+"' to the macro '"+str(macro.name)+"'."

            if 'MACRO' in line:
                macro = Macro(line.split()[1]) # Create a Macro object. The name of the macro is the second word in the line 'MACRO ...'
                macros[macro.name] = macro

            if 'SIZE' in line:
                # Sample line: SIZE 0.42 BY 0.24 ;
                # width BY height
                size = line.split()
                macro.setWidth(float(size[1]))
                macro.setHeight(float(size[3]))


            line = f.readline()

    return macros


if __name__ == "__main__":

    lef_file = "/home/para/dev/def_parser/lef/N07_7.5TMint_7.5TM2_M1open.lef"

    macros = parse_lef(lef_file)
    output = ""

    for key in macros:
        output += "{}, {}, {} by {}\n".format(macros[key].name, str(len(macros[key].pins)), macros[key].width, macros[key].height)

    # Compute mean width
    widths = []
    for key, macro in macros.items():
        widths.append(macro.width)
    output += "Mean width: {}\n".format(np.mean(widths))

    print output

