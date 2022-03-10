"""
Usage:
    verilogparser.py     [-n <netlist>]
    verilogparser.py     (--help|-h)

Options:
    -n <netlist>       Path to netlist
    -h --help           Print this help
"""

import re
import os
import random
from alive_progress import alive_bar
from docopt import docopt

# VERILOG_FILE = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile_flat_synth/tile_flat.v"
# VERILOG_FILE = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile/forQD/tile_noBuffers.v"
# VERILOG_FILE = "/home/para/dev/def_parser/Mempool_Tile_in3_2021-12-10/tile/forQD/tile_withBuffers.v"
# VERILOG_FILE = "/home/para/dev/def_parser/MemPool/tilePnR_2021-05-05/tile_noBuff.v"
# VERILOG_FILE = "/home/para/tmp/netlist.v"

class Instance:
    def __init__(self, stdCell, name):
        self.stdCell = stdCell # str
        # self.pin = dict() # {pin name : net name}
        self.nets = [] # [str], list of net names
        self.name = name # str

class Net:
    def __init__(self, name):
        self.name = name # str
        self.instances = [] # [instance name]


def exportToCsv():
    outStr = "stdcell, instance, nets\n"
    for instance in instances.values():
        outStr += instance.stdCell
        outStr += ","
        outStr += instance.name
        for netName in instance.nets:
            outStr += ",{}".format(netName)
        outStr += "\n"
    csvOutFile = "_".join([VERILOG_FILE.split(".v")[0], "instances.csv"])
    print(csvOutFile)
    with open(csvOutFile, 'w') as f:
        f.write(outStr)

def generateRandPartitions():
    outStr = ""
    outStrTcl = ""
    for instance in instances.keys():
        die = random.choice(['0','1'])
        outStr += instance + " " + die + '\n'
        if die == '1':
            outStrTcl += "lappend listsA [list tile {{{}}} ];\n".format(instance)

    partOutFile = "_".join([VERILOG_FILE.split(".v")[0], "random_part.txt"])
    tclOutFile = "_".join([VERILOG_FILE.split(".v")[0], "random_part.tcl"])
    print(partOutFile)
    print(tclOutFile)
    with open(partOutFile, 'w') as f:
        f.write(outStr)
    with open(tclOutFile, 'w') as f:
        f.write(outStrTcl)

if __name__ == "__main__":
    args = docopt(__doc__)
    
    if args["-n"]:
        VERILOG_FILE = args["-n"]

    instances = dict()
    nets = dict()

    with open(VERILOG_FILE, 'r') as f:
        print("Reading input Verilog netlist: {}".format(VERILOG_FILE))
        lines = f.readlines()

    print("Parsing Verilog netlist")
    entry = ""
    for line in lines:
        # print("Parsing line: {}".format(line))
        entry += line
        if not ';' in line:
            continue
        else:
            # print("Regex on entry: {}".format(entry))
            match = re.search('^\s+([A-Za-z0-9_]+)\s+([^\s\(;]*)\s*\([^\)]', entry)
            # Typical pattern is 'STANDARD_CELL instance_name (.PIN1(netA),'
            # We don't want fillers and tap which look like 'STD inst ()'
            if match:
                stdcell = match.group(1).strip()
                instanceName = match.group(2).strip()
                # print(stdcell)
                # print(instanceName)
                instance = Instance(stdcell, instanceName)
                instances[instanceName] = instance
            ml = re.split("\.[A-Z0-9]+\s*", entry)
            for candidate in ml[1:]:
                match = re.search('^\s*\(\s*([^\)]+)\s*\)', candidate)
                if match:
                    netName = match.group(1).strip()
                    netName = re.sub(r'\s+', ' ', netName)
                    # print(netName)
                    instance.nets.append(netName)
                    if netName not in nets.keys():
                        net = Net(netName)
                        net.instances.append(instanceName)
                        nets[netName] = net
                    else:
                        nets[netName].instances.append(instanceName)
            entry = ""

    exportToCsv()

    # generateRandPartitions()


