"""
Usage:
    heatmap.py (-d <directives>) (-t <sta-report>) [-s <cell_sizes>]
    heatmap.py (--help|-h)

Options:
    -d <directives> Directives file (.part, no escape chars)
    -t <sta-report> STA report (.rpt)
    -s <cell_sizes> CellSizes.out
    -h --help       Print this help
"""

from docopt import docopt
from alive_progress import alive_bar
import sys
import re

if __name__ == "__main__":

    balanceMitigation = False

    args = docopt(__doc__)
    if args["-d"]:
        directivesFile = args["-d"]
    if args["-t"]:
        staFile = args["-t"]
    if args["-s"]:
        cellSizesFile = args["-s"]
        balanceMitigation = True

    with open(directivesFile, 'r') as f:
        lines = f.readlines()


    ##############################################
    # Extract cells and the die on which they lie
    ##############################################
    cells = dict() # {cell name : die number 0 or 1}
    for line in lines:
        cells[line.split(' ')[0]] = int(line.split(' ')[1])

    if balanceMitigation:
        #####################
        # Extract cell sizes
        #####################
        cellSizes = dict() # {cell name: area [float]}
        with open(cellSizesFile, 'r') as f:
            lines = f.readlines()
        for line in lines[1:]:
            cellSizes[line.split(' ')[0].replace('\\', '')] = float(line.split(' ')[1]) * float(line.split(' ')[2])

        ############################################
        # What is the current partitioning balance?
        ############################################
        botArea = 0
        topArea = 0
        for cell in cells:
            if cells[cell] == 0:
                botArea += cellSizes[cell]
            elif cells[cell] == 1:
                topArea += cellSizes[cell]
        balance = botArea/topArea
        currentBalance = balance
        print("Balance of bottom die area: {}".format(balance))

    #############################
    # Set output files full path
    #############################
    directivesPostSTAFile = '_'.join(['.'.join(directivesFile.split('.')[:-1]), "post-STA.txt"])
    print(directivesPostSTAFile)
    fixfilePostSTAFile = '_'.join(['.'.join(directivesFile.split('.')[:-1]), "post-STA_fixfile.hgr"])

    with open(staFile, 'r') as f:
        lines = f.readlines()

    startDie = 0 # 0 = bottom, 1 = top
    endDie = 0 # 0 = bottom, 1 = top
    level = 0   # 0 => start and end in bot, no transition allowed
                # 1 => start and end in top, no transition allowed
                # 2 => start in bot and end in top, max 1 transition allowed
                # 3 => start in top and end in bot, max 1 transition allowed
    inPath = False
    cellsInPath = list()
    movedCellsCount = 0
    pathAnalysed = 0
    print("Checking the paths")
    with alive_bar(len(lines)) as bar:
        for line in lines:
            bar()
            if not inPath:
                #####################
                # Check type of path
                #####################
                if "Endpoint:" in line:
                    if "topDiei" in line:
                        endDie = 1
                    elif "botDiei" in line:
                        endDie = 0
                if "Beginpoint:" in line:
                    if "topDiei" in line:
                        startDie = 1
                        if endDie == 0:
                            level = 3
                        elif endDie == 1:
                            level = 1
                    elif "topDiei" in line:
                        startDie = 0
                        if endDie == 0:
                            level = 0
                        elif endDie == 1:
                            level = 2
                if "Timing Path:" in line:
                    inPath = True
                    pathAnalysed += 1
                    # print("I'm in path {}".format(pathAnalysed))
            elif inPath:
                if "VIOLATED" in line or "Other End Path:" in line:
                    inPath = False
                    cellsInPath = list()
                    # print("Not in path anymore")

                match = re.search('^(botDiei|topDiei)/([^/]+)/[A-Z0-9]+\s', line.strip())
                # print("Level {}".format(level))
                if match:
                    die = match.group(1)
                    cell = match.group(2)
                    if cell in cells:
                        cellsInPath.append(cell)

                if "-----------------------" in line and len(cellsInPath) > 0:
                    if level == 0:
                        # All cells should be on bottom.
                        for cell in cellsInPath:
                            cells[cell] = 0
                    elif level == 1:
                        # All cells should be on top.
                        for cell in cellsInPath:
                            cells[cell] = 1
                    ###########################################
                    # Get over the list of cells and fix them.
                    ###########################################
                    if balanceMitigation:
                        # print("Balance mitigation activated")
                        pathTotalArea = 0
                        for cell in cellsInPath:
                            pathTotalArea += cellSizes[cell]
                        pivotPointArea = pathTotalArea*balance
                        if level == 2:# bot -> top
                            sumArea = 0 # Area of cells to fix in bottom
                            for i in range(len(cellsInPath)):
                                cell = cellsInPath[i]
                                if (sumArea + cellSizes[cell]) < pivotPointArea:
                                    sumArea += cellSizes[cell]
                                    cells[cell] = 0
                                elif (sumArea + cellSizes[cell]) >= pivotPointArea:
                                    if currentBalance <= balance:
                                        # Deficit in bottom
                                        sumArea += cellSizes[cell]
                                        cells[cell] = 0
                                        for cell in cellsInPath[i+1:]:
                                            cells[cell] = 1
                                        # print("currentBalance {}".format(currentBalance))
                                        currentBalance = (botArea+sumArea)/(topArea-(pathTotalArea-sumArea)) # bot/top
                                        # print("currentBalance (post-mod) {}".format(currentBalance))
                                        break
                                    elif currentBalance > balance:
                                        # Overpopulation in bottom
                                        for cell in cellsInPath[i+1:]:
                                            cells[cell] = 1
                                        currentBalance = (botArea+sumArea)/(topArea-(pathTotalArea-sumArea)) # bot/top
                                        break
                        if level == 3:# top -> bot
                            sumArea = pathTotalArea # Area of cells to fix in bottom
                            # This time we decrement the total area because we assume that everything is in the bottom
                            # and that we fix cells in the top one at a time.
                            for i in range(len(cellsInPath)):
                                cell = cellsInPath[i]
                                if (sumArea - cellSizes[cell]) > pivotPointArea:
                                    sumArea -= cellSizes[cell]
                                    cells[cell] = 1
                                elif (sumArea - cellSizes[cell]) <= pivotPointArea:
                                    if currentBalance <= balance:
                                        # Deficit in bottom
                                        for cell in cellsInPath[i:]:
                                            cells[cell] = 0
                                        currentBalance = (botArea+sumArea)/(topArea-(pathTotalArea-sumArea)) # bot/top
                                        break
                                    elif currentBalance > balance:
                                        # Overpopulation in bottom
                                        cells[cell] = 1
                                        for cell in cellsInPath[i+1:]:
                                            cells[cell] = 0
                                        currentBalance = (botArea+sumArea)/(topArea-(pathTotalArea-sumArea)) # bot/top
                                        break
                    else:
                        #######################################################################
                        # Default: split the path in half based on the amount of cells in path
                        #######################################################################
                        # print("No balance mitigation")
                        if level == 2:
                            # Half the list on bottom, other half in top
                            for cell in cellsInPath[:int(len(cellsInPath)/2)]:
                                cells[cell] = 0
                            for cell in cellsInPath[int(len(cellsInPath)/2):]:
                                cells[cell] = 1
                        if level == 3:
                            # Half the list on top, other half in bottom
                            for cell in cellsInPath[:int(len(cellsInPath)/2)]:
                                cells[cell] = 1
                            for cell in cellsInPath[int(len(cellsInPath)/2):]:
                                cells[cell] = 0

    if balanceMitigation:
        print("Final bottom area balance: {}".format(currentBalance))
    print("Analysed paths: {}".format(pathAnalysed))

    postSTADirectivesStr = ""
    fixfileStr = ""
    for cell in cells:
        postSTADirectivesStr += cell.strip() + " " + str(cells[cell]).strip() + "\n"
        fixfileStr += str(cells[cell]).strip() + "\n"

    with open(directivesPostSTAFile, 'w') as f:
        f.write(postSTADirectivesStr)
    with open(fixfilePostSTAFile, 'w') as f:
        f.write(fixfileStr)