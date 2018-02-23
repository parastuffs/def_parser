from __future__ import division
import def_parser
import Image
import random
from natsort import natsorted # https://pypi.python.org/pypi/natsort
import os
from sets import Set


if __name__ == "__main__":
    """
    The folder tree should be as follows:
    Main folder
    |_ Cluster level x
        |_ partition
    """
    mainDir = "/home/para/dev/def_parser/2018-02-21_10-11-08"

    clusterLevels = []

    # Array of arrays of sets: [[Set_partition0, Set_partition1], ... ]
    # There is on array of sets per clustering level.
    partitionSets = []

    # Partitions extraction
    for clusterDir in natsorted(os.listdir(mainDir)):
        clusterDir = os.path.join(mainDir, clusterDir)
        if os.path.isdir(clusterDir):
            clusterLevels.append(clusterDir.split('_')[-1])
            for partitionDir in natsorted(os.listdir(clusterDir)):
                partitionDir = os.path.join(clusterDir, partitionDir)
                if os.path.isdir(partitionDir):
                    for partitionFile in natsorted(os.listdir(partitionDir)):
                        # I just want to compare 'metis_01'.
                        if "metis_01" in partitionFile and partitionFile.split('.')[-1] == "part":

                            set0 = Set()
                            set1 = Set()

                            with open(os.path.join(partitionDir, partitionFile), 'r') as f:
                                for line in f.readlines():
                                    gate = line.split()[0]
                                    die = int(line.split()[1])

                                    if die == 0:
                                        set0.add(gate)
                                    elif die == 1:
                                        set1.add(gate)

                            partitionSets.append([set0, set1])

    """
    Formating the output file:

    Total gates, <total gates>
    , <cluster level 2>, ..., <cluster level n>
    <cluster level 1>, <common gates with 2>, ..., <common gates with n>
    <cluster level 2>, , <common gates with 3>, ..., <common gates with n>
    ...
    <cluster level n-1>, , ..., <common gates with n>
    """
    output = ""
    totGates = len(partitionSets[0][0]) + len(partitionSets[0][1])
    output += "Total gates, " + str(totGates) + "\n"

    for i in range(1,len(clusterLevels)):
        output += "," + str(clusterLevels[i])
    output += "\n"

    outputRelative = output

    for i in range(len(partitionSets)-1):
        output += str(clusterLevels[i])
        output += "," * i
        outputRelative += str(clusterLevels[i])
        outputRelative += "," * i
        for j in range(i+1, len(partitionSets)):
            commonGates = len(partitionSets[i][0].intersection(partitionSets[j][0])) + len(partitionSets[i][1].intersection(partitionSets[j][1]))
            output += "," + str(commonGates)

            # If we have less than half of the gates in the same partition,
            # we can simply invert the result as it corresponds to inverting
            # the two dies.
            # The most similar partitions are at 100%,
            # the least similar at 50%
            if commonGates < 0.5*totGates:
                commonGates = totGates - commonGates
            outputRelative += "," + str(100*commonGates/totGates)
        output += "\n"
        outputRelative += "\n"


    output += "\n" + outputRelative
    # print output

    with open(os.path.join(mainDir, "part-comp_metis_01.csv"), 'w') as f:
        f.write(output)