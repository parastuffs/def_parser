import def_parser
from PIL import Image



if __name__ == "__main__":

    stdCellsTech = "gsclib045"
    stdCellsTech = "osu018"
    
    def_parser.extractStdCells(stdCellsTech)
    if def_parser.MEMORY_MACROS:
        def_parser.extractMemoryMacros(14,4)

    # If you change the deffile, also change the leffile, MEMORY_MACROS and UNITS_DISTANCE_MICRONS
    # TODO make this into cli parameter
    # def_parser.deffile = "7nm_Jul2017/ldpc.def"
    # def_parser.deffile = "7nm_Jul2017/BoomCore.def"
    # def_parser.deffile = "7nm_Jul2017/flipr.def"
    # def_parser.deffile = "7nm_Jul2017/ccx.def"
    def_parser.deffile = "7nm_Jul2017/SPC/spc.def" # Don't forget to turn the MEMORY_MACROS on.
    def_parser.deffile = "SmallBOOM_CDN45/SmallBOOM.def"
    def_parser.deffile = "armM0/ArmM0_all.def"
    def_parser.deffile = "msp430/openMSP430.def"


    def_parser.design = def_parser.Design()
    def_parser.design.ReadArea()
    def_parser.design.ExtractCells()

    imgW = int(def_parser.design.width*100) # Width of the design in 100^-1 um
    imgH = int(def_parser.design.height*100)
    imgSize = (imgW) * (imgH)
    data = [0] * imgSize

    for key in def_parser.design.gates:
    	x = def_parser.design.gates[key].x
    	y = def_parser.design.gates[key].y
    	index = (int(y*100) * (imgW) ) + int(x*100)
    	data[index] = 255

    print("Create the image (" + str(imgW) + ", " + str(imgH) + ")")
    img = Image.new('L', (imgW, imgH))
    print("Put data")
    img.putdata(data)
    print("save image")
    img.save('out.png')
    # print "show image"
    # img.show()