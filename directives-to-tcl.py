"""
Usage:
    verilogparser.py     [-f <directives>]
    verilogparser.py     (--help|-h)

Options:
    -f <directives>     Path to netlist
    -h --help           Print this help
"""

from docopt import docopt

if __name__ == "__main__":
    args = docopt(__doc__)
    
    if args["-f"]:
        directives_file = args["-f"]

    # with open("/home/para/Documents/ULB/phd/experiments/2022-02/2021-12-10_17-17-47_mempool-tile-bl_onetoone/tile_noBuffers_onetoone_0/partitions_2021-12-10_18-45-06_hMetis_MoL/metis_01_NoWires_area.hgr.part_clean", 'r') as f:
    with open(directives_file, 'r') as f:
        lines = f.readlines()

    outString=""
    for line in lines:
        instance = line.split(' ')[0]
        die = line.split(' ')[1].strip()
        if die == "1":
            outString += "lappend listsA [list tile {{{}}} ];\n".format(instance)

    outputfile = "_".join([".".join(directives_file.split(".")[:-1]), "directives.tcl"])
    print(outputfile)
    with open(outputfile, 'w') as f:
      f.write(outString)
