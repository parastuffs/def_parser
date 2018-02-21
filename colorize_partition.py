import def_parser
import Image
import random
from natsort import natsorted # https://pypi.python.org/pypi/natsort
import os

"""
Partition 0: (255, 0, 0)
Partition 1: (0, 0, 255)
"""



if __name__ == "__main__":

    def_parser.MEMORY_MACROS = False # spc: True, others: False
    def_parser.UNITS_DISTANCE_MICRONS = 10000 #flipr, boomcore, ldpc
    # def_parser.UNITS_DISTANCE_MICRONS = 1000  #ccx, spc

    # ldpc, boomcore, flipr: "7nm"
    # ccx, spc: "45nm"
    def_parser.extractStdCells("7nm")
    if def_parser.MEMORY_MACROS:
        def_parser.extractMemoryMacros(14,4)

    # If you change the deffile, also change the leffile, MEMORY_MACROS and UNITS_DISTANCE_MICRONS
    # def_parser.deffile = "7nm_Jul2017/ldpc.def"
    # def_parser.deffile = "ldpc_4x4/ldpc-4x4.def"
    def_parser.deffile = "7nm_Jul2017/BoomCore.def"
    # def_parser.deffile = "7nm_Jul2017/flipr.def"
    # def_parser.deffile = "7nm_Jul2017/ccx.def"
    # def_parser.deffile = "7nm_Jul2017/SPC/spc.def" # Don't forget to turn the MEMORY_MACROS on.


    """
    The folder tree should be as follows:
    Main folder
    |_ Cluster level x
        |_ partition
    """
    # partitionFile = "/home/para/dev/metis_unicorn/temp_design/metis_02_1-NoWires_area.hgr.part"
    # partitionFile = "/home/para/dev/def_parser/2018-01-24_19-37-08/BoomCore_random_9/partitions_2018-02-20_13-03-40/metis_02_1-NoWires_area.hgr.part"
    mainDir = "/home/para/dev/def_parser/2018-01-24_19-37-08/"

    def_parser.design = def_parser.Design()
    def_parser.design.ReadArea()
    def_parser.design.ExtractCells()

    imgW = int(def_parser.design.width*10) # Width of the design in 10^-1 um
    imgH = int(def_parser.design.height*10)
    imgSize = (imgW) * (imgH)
    data = [0] * imgSize

    for clusterDir in natsorted(os.listdir(mainDir)):
        clusterDir = os.path.join(mainDir, clusterDir)
        if os.path.isdir(clusterDir):
            for partitionDir in natsorted(os.listdir(clusterDir)):
                partitionDir = os.path.join(clusterDir, partitionDir)
                if os.path.isdir(partitionDir):
                    for partitionFile in natsorted(os.listdir(partitionDir)):
                        # I just want to generate the image for the 'metis_01' file.
                        # CF 2017-02-21, MPD: "Comme disait mon pere, c'est des moules dans du sirop.", en parlant du projet batiment.
                        if "metis_01" in partitionFile and partitionFile.split('.')[-1] == "part":

                            clusters = dict()
                            partColors = [(255, 0, 0), (0, 0, 255)]

                            with open(os.path.join(partitionDir, partitionFile), 'r') as f:
                                for line in f.readlines():
                                    gate = line.split()[0]
                                    x = def_parser.design.gates.get(gate).x
                                    y = def_parser.design.gates.get(gate).y
                                    # print x
                                    # print y
                                    index = (int(y*10) * (imgW) ) + int(x*10)
                                    data[index] = partColors[int(line.split()[1])]


                            # for k in clusters:
                            #     r = int(random.uniform(0, 255))
                            #     g = int(random.uniform(0, 255))
                            #     b = int(random.uniform(0, 255))
                            #     for gate in clusters[k]:
                            #         x = def_parser.design.gates.get(gate).x
                            #         y = def_parser.design.gates.get(gate).y
                            #         # print x
                            #         # print y
                            #         index = (int(y*10) * (imgW) ) + int(x*10)
                            #         data[index] = (r, g, b)

                            print "Create the image (" + str(imgW) + ", " + str(imgH) + ")"
                            img = Image.new('RGB', (imgW, imgH))
                            print "Put data"
                            img.putdata(data)
                            print "save image"
                            outfile = os.path.join(partitionDir, clusterDir.split('/')[-1] + ".png")
                            img.save(outfile)
