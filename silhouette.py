"""
Usage:
    silhouette.py (--compute)
    silhouette.py (--boxplot)
    silhouette.py (--help|-h)

Options:
    --compute       Compute silhouette scores and store them
    --boxplot       Draw a boxplot from the previously computed scores
    -h --help       Print this help
"""


from math import *
import logging, logging.config
import matplotlib.pyplot as plt
from alive_progress import alive_bar
from multiprocessing import Process, Queue
import os
from docopt import docopt
import glob
from natsort import natsorted
import numpy as np

# CLUSTER_FILE = "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_10000/ClustersInstances.out"
# CLUSTER_FILE = "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_2/ClustersInstances.out"
CLUSTER_FILE = "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_1000/ClustersInstances.out"
CELL_FILE = "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/CellCoord.out"

MAX_PROCESSES = 6


def initialise(clusterFile, cells, clustersCentroids, cellCluster, clusterCells, clusters):
    with open(CELL_FILE, 'r') as f:
        lines = f.readlines()

    with alive_bar(len(lines)) as bar:
        print("Extracting cells")
        for line in lines:
            bar()
            cells[line.split(',')[1]] = [float(line.split(',')[2]),float(line.split(',')[3])]
    print("Total cells: {}".format(len(cells)))

    with open(clusterFile+"/ClustersInstances.out", 'r') as f:
        lines = f.readlines()

    with alive_bar(len(lines)) as bar:
        print("Extracting clusters")
        for line in lines:
            bar()
            line = line.strip()
            if len(line.split(' ')) > 1:
                # Ignore empty clusters
                clusterID = int(line.split(' ')[0])
                clusters[clusterID] = list()
                clusterCells[clusterID] = list()
                for cell in line.split(' ')[1:]:
                    clusters[clusterID].append(cells[cell])
                    cellCluster[cell] = clusterID
                    clusterCells[clusterID].append(cell)

    with alive_bar(len(clusters)) as bar:
        print("Calculating clusters centroids")
        for cID in clusters.keys():
            bar()
            if len(clusters[cID]) > 1:
                clustersCentroids[cID] = [
                    sum(clusters[cID][i][0] for i in range(1,len(clusters[cID])))/(len(clusters[cID]) - 1),# x
                    sum(clusters[cID][i][1] for i in range(1,len(clusters[cID])))/(len(clusters[cID]) - 1) # y
                    ]
            else:
                clustersCentroids[cID] = clusters[cID][0]


def exportCSV(silhouettes, clusterCount):
    fileName = os.sep.join([CELL_FILE.split(os.sep)[-2],"silhouette_"+clusterCount+"_clusters.csv"])

    s = ','.join(map(str, silhouettes))

    with open(fileName, 'w') as f:
        f.write(s)


def distance(a, b):
    '''
    Manhattan's distance between a and b.
    Parameters:
    a : list
        [x, y] as floats
    b : list
        [x, y] as floats

    Return:
    float
    '''

    return abs(a[0] - b[0]) + abs(a[1] + b[1])


def silhouette(cells, clustersCentroids, cellCluster, clusterCells, cellsKeys, queue):
    silhouettes = list()
    with alive_bar(len(cellsKeys)) as bar:
        print("Silhouette per cell")
        for i in cellsKeys:
            bar()
            a = 0
            cID = cellCluster[i]
            if len(clusterCells[cID]) == 1:
                s = 0
            else:
                for j in clusterCells[cID]:
                    a += distance(cells[i],cells[j])
                a /= (len(clusterCells) - 1)

                # Find closest cluster's centroid from the cell i
                closestCentroid = float('inf')
                closestCluster = 0
                for cID in clustersCentroids.keys():
                    d = distance(cells[i], clustersCentroids[cID])
                    if d > 0 and d < closestCentroid:
                        closestCentroid = d
                        closestCluster = cID
                b = 0
                for j in clusterCells[closestCluster]:
                    b += distance(cells[i],cells[j])
                b /= len(clusterCells[closestCluster])

                s = (b-a)/max(a,b)
            queue.put(s)
    print("Reached the end of my process :)")


def compute():
    clusterFiles = ["/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_2",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_4",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_8",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_10",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_16",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_32",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_50",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_150",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_200",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_250",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_300",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_350",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_400",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_450",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_500",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_600",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_700",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_800",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_900",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_1000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_2000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_3000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_4000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_5000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_6000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_7000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_8000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_9000",
                    "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/BoomCore_PlacedNoBuff_kmeans-geometric_10000"
                    ]


    # for f in reversed(clusterFiles):
    for f in clusterFiles:

        # Dictionary of cells and their coordinates
        cells = dict() # Name: [x, y]

        # Dictionary of clusters and the coordinates of the cells inside it
        clusters = dict() # ClusterID: [[x1,y1],...,[xn,yn]]

        # Dictionary of clusters and their centroids
        clustersCentroids = dict() # ClusterID: [x,y]

        # Dictionary of cells of the ID of the clusters to which they belong
        cellCluster = dict() # Cell name : cluster ID

        # Dictionary of clusters and the name of the cells they contain
        clusterCells = dict() # cluster ID : [cell name 1,..., cell name n]

        # # Dictionary of silhouette value for each cell
        # cellSil = dict() # Cell name : sihouette coefficient

        silhouettes = list()

        clusterCount = f.split('_')[-1]

        print("################################")
        print("Working with {} clusters".format(clusterCount))

        initialise(f, cells, clustersCentroids, cellCluster, clusterCells, clusters)

        ##############
        # SILHOUETTE #
        ##############

        queue = Queue()
        # print("Queue size: {}".format(queue.qsize()))
        processes = list()
        for i in range(MAX_PROCESSES):
            p = Process(target=silhouette, args=(cells, clustersCentroids, cellCluster, clusterCells, list(cells.keys())[ceil(i*len(cells)/MAX_PROCESSES):ceil((i+1)*len(cells)/MAX_PROCESSES)], queue,))
            processes.append(p)
            p.start()
            # If the process is not started as a daemon, it is automatically joined.


        isAlive = True
        while isAlive:
            if queue.qsize() > 0:
                isAlive = True
                # The queue needs to be emptied during the execution, otherwise the pipe to which it's connected will be full and the processes will hang.
                silhouettes.append(queue.get())
            else:
                isAlive = False
            for p in processes:
                isAlive |= p.is_alive()

        exportCSV(silhouettes, clusterCount)


def boxplot():
    rootDir = "/home/para/dev/def_parser/2021-11-23_09-10-28_boomcore-2020-pp-bl_kmeans-geometric/"
    os.chdir(rootDir)

    silhouettesList = list() # List of lists of silouhettes scores
    xTicks = list() # List of x ticks for the plot, aka the amount of clusters
    silhouettesMeans = list() # List of mean values of all silhouette scores for one clustering

    with alive_bar():
        # All csv files are one-liners with comma-separated float values.
        for file in natsorted(glob.glob("silhouette*clusters.csv")):
            # print("Opening {}".format(file))
            xTicks.append(int(file.split('_')[1]))
            with open(file, 'r') as f:
                silhouettesList.append(list(map(float, f.readline().split(','))))
            silhouettesMeans.append(np.mean(silhouettesList[-1]))

    plt.figure()
    plt.title("Cells silhouette")
    flierprops = dict(marker='o', markersize=1, linestyle='none')
    plt.boxplot(silhouettesList, showmeans=True, meanline=True, showfliers=True, flierprops=flierprops)
    plt.xticks([i+1 for i in range(len(xTicks))],xTicks,rotation='vertical')
    plt.figure()
    plt.title("Average silhouette scores")
    plt.plot(xTicks,silhouettesMeans) 
    plt.show()


if __name__ == "__main__":


    args = docopt(__doc__)

    if args["--compute"]:
        compute()
    elif args["--boxplot"]:
        boxplot()

    

