import def_parser
from PIL import Image
import random
import os

# Scale factor from 1um. 10 => 100nm means 1 pixel is 100 nm
SCALE_FACTOR = 1

colors = [  [53, 235, 30],
            [30, 230, 235],
            [30, 82, 235],
            [235, 30, 223],
            [235, 30, 43],
            [235, 148, 30],
            [227, 235, 30],
            [135, 135, 135]
        ]




if __name__ == "__main__":


    clusterInsFile = "/home/para/dev/def_parser/2019-07-16_16-16-09_smallboom_kmeans-geometric/SmallBOOM_kmeans-geometric_100/ClustersInstances.out"
    tech = ""

    if "ldpc-4x4-serial" in clusterInsFile:
        def_parser.deffile = "ldpc_4x4_serial.def/ldpc-4x4-serial.def"
        tech = "7nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 10000
    elif "ldpc-4x4" in clusterInsFile:
        def_parser.deffile = "ldpc_4x4/ldpc-4x4.def"
        tech = "7nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 10000
    elif "ldpc" in clusterInsFile:
        def_parser.deffile = "7nm_Jul2017/ldpc.def"
        tech = "7nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 10000
    elif "BoomCore" in clusterInsFile:
        def_parser.deffile = "7nm_Jul2017/BoomCore.def"
        tech = "7nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 10000
    elif "flipr" in clusterInsFile:
        def_parser.deffile = "7nm_Jul2017/flipr.def"
        tech = "7nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 10000
    elif "ccx" in clusterInsFile:
        def_parser.deffile = "7nm_Jul2017/ccx.def"
        tech = "45nm"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 1000
    elif "spc" in clusterInsFile:
        def_parser.deffile = "7nm_Jul2017/SPC/spc.def"
        tech = "45nm"
        def_parser.MEMORY_MACROS = True
        def_parser.UNITS_DISTANCE_MICRONS = 1000
    elif "smallboom" in clusterInsFile:
        def_parser.deffile = "SmallBOOM_CDN45/SmallBOOM.def"
        tech = "gsclib045"
        def_parser.MEMORY_MACROS = False
        def_parser.UNITS_DISTANCE_MICRONS = 2000


    def_parser.extractStdCells(tech)
    if def_parser.MEMORY_MACROS:
        def_parser.extractMemoryMacros(14,4)

    # If you change the deffile, also change the leffile, MEMORY_MACROS and UNITS_DISTANCE_MICRONS
    # TODO make this into cli parameter
    
    # d
    # 
    # def_parser.deffile = "7nm_Jul2017/ccx.def"
    # def_parser.deffile = "7nm_Jul2017/SPC/spc.def" # Don't forget to turn the MEMORY_MACROS on.

    def_parser.design = def_parser.Design()
    def_parser.design.ReadArea()
    def_parser.design.ExtractCells()

    imgW = int(def_parser.design.width*SCALE_FACTOR) # Width of the design in 10^-1 um
    imgH = int(def_parser.design.height*SCALE_FACTOR)
    imgSize = (imgW) * (imgH)
    data = [0] * imgSize

    clusters = dict()

    with open(clusterInsFile, 'r') as f:
        for line in f.readlines():
            clusters[line.split()[0]] = line.split()[1:]

    for i, k in enumerate(clusters):
        if i < len(colors):
            r = colors[i][0]
            g = colors[i][1]
            b = colors[i][2]
        else:
            r = int(random.uniform(0, 255))
            g = int(random.uniform(0, 255))
            b = int(random.uniform(0, 255))
        for gate in clusters[k]:
            x = def_parser.design.gates.get(gate).x
            y = def_parser.design.gates.get(gate).y
            # print x
            # print y
            index = (int(y*SCALE_FACTOR) * (imgW) ) + int(x*SCALE_FACTOR)
            data[index] = (r, g, b)

    print "Create the image (" + str(imgW) + ", " + str(imgH) + ")"
    img = Image.new('RGB', (imgW, imgH))
    print "Put data"
    img.putdata(data)
    filename = os.path.join(os.sep.join(clusterInsFile.split(os.sep)[:-1]),clusterInsFile.split(os.sep)[-2]) + "_cluster_colors.png"
    print("save image as ", filename)

    img.save(filename)
    # print "show image"
    # img.show()