from __future__ import division
import def_parser
import Image
import random
from natsort import natsorted # https://pypi.python.org/pypi/natsort
import os



if __name__ == "__main__":
    """
    The folder tree should be as follows:
    Main folder
    |_ Cluster level x
        |_ partition
    """
    mainDir = "/home/para/dev/def_parser/2018-01-24_22-03-05"

    # Array of dictionaries, each containing {str(gate name): int(die)}
    partitions = []
    clusterLevels = []

    # Partitions extraction
    for clusterDir in natsorted(os.listdir(mainDir)):
        clusterLevels.append(clusterDir.split('_')[-1])
        clusterDir = os.path.join(mainDir, clusterDir)
        if os.path.isdir(clusterDir):
            for partitionDir in natsorted(os.listdir(clusterDir)):
                partitionDir = os.path.join(clusterDir, partitionDir)
                if os.path.isdir(partitionDir):
                    for partitionFile in natsorted(os.listdir(partitionDir)):
                        # I just want to compare 'metis_01'.
                        if "metis_01" in partitionFile and partitionFile.split('.')[-1] == "part":

                            partition = dict()

                            with open(os.path.join(partitionDir, partitionFile), 'r') as f:
                                for line in f.readlines():
                                    partition[line.split()[0]] = int(line.split()[1])
                            partitions.append(partition)

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
    output += "Total gates, " + str(len(partitions[0])) + "\n"

    for i in range(1,len(clusterLevels)):
        output += "," + str(clusterLevels[i])
    output += "\n"

    outputRelative = output

    for i in range(len(partitions)):
        output += str(clusterLevels[i])
        output += "," * i
        outputRelative += str(clusterLevels[i])
        outputRelative += "," * i
        for j in range(i+1, len(partitions)):
            commonGates = 0
            for k in partition:
                if partitions[j].get(k) == partitions[i][k]:
                    commonGates += 1
            output += "," + str(commonGates)
            outputRelative += "," + str(100*commonGates/len(partitions[0]))
        output += "\n"
        outputRelative += "\n"


    output += "\n" + outputRelative
    # print output

    with open(os.path.join(mainDir, "part-comp_metis_01.csv"), 'w') as f:
        f.write(output)