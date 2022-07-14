"""
Usage:
    heatmap.py (-d <dir>) [-c <dir>] [-p <file>] [-n <file>] [-r <max-res>] [--3D]
    heatmap.py (--help|-h)

Options:
    -d <path>       Path to design folder
    -c <dir>        Sub dir from <path> to a folder containing ClustersInstances.out
    -p <file>       Partition file with lines such as '<cell name> <O/1>' (.part)
    -n <file>       File with nets cut by partition (connectivity_partition.txt)
    -r <max-res>    Maximum pixel resolution. A 4x4 display uses max-res/2, /5 and /10 as well.
                    Default: 300
    --3D            Display 3D pins as yellow pixels, FRONT_BUMP instances
    -h --help       Print this help
"""

from math import *
import locale
import os
import datetime
import errno
import random
from docopt import docopt
import logging, logging.config
import numpy as np
import sys
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import statistics
import math
from alive_progress import alive_bar
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

RANDOM_SEED = 0 # Set to 0 if no seed is used, otherwise set to seed value.


def loadDesign(display3DPins):
    """
    CellSizes.out:
        <cell name> <width [float]> <height [float]>
    CellCoord.out:
        <net name>, <cell name>, <x [float]>, <y [float]>

    Parameters:
    -----------
    display3DPins : boolean
        If true, load pins

    Return
    ------
    cells : {}
    maxX : float
    maxY : float
    pins : []
    """
    cells = {} # {cell name: [x,y,width, height]}
    maxX = 0
    maxY = 0
    with open("CellCoord.out", 'r') as f:
        lines = f.readlines()

        for line in lines:
            cells[line.split(',')[1]] = [float(line.split(',')[2]), float(line.split(',')[3])]
    with open("CellSizes.out", 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            cellName = line.split(' ')[0]
            if cellName in cells:
                # Continue only if the cellName has a coordinate in the cells dictionary.
                # It might happen that is does not, such as 3D bump in 3D ICs.
                cells[cellName].extend([cells[cellName][0] + float(line.split(' ')[1]), cells[cellName][1] + float(line.split(' ')[2])])
                maxX = max(maxX, cells[cellName][2])
                maxY = max(maxY, cells[cellName][3])

    pins = []
    if display3DPins:
        with open("uBumps.out", 'r') as f:
            lines = f.readlines()
        for line in lines[1:]:
            pins.append([float(line.split(' ')[1]), float(line.split(' ')[2])])
    return cells, maxX, maxY, pins

def generateHeatmap(cells, maxX, maxY, dimension=300, display3DPins=False, pins=None):
    """
    Parameters
    ----------
    cells : {cell name : [x1, y1, x2, y2]}
    maxX : float
    maxY : float
    display3DPins : boolean
    pins : [[x, y]]
    """


    fig, axs = plt.subplots(2,2)

    for counter, dimension in enumerate([dimension/10, dimension/5, dimension/2, dimension]):
        imgW = math.floor(dimension)
        imgH = int(imgW * (maxY/maxX))

        data = np.zeros(shape=(imgW+2,imgH+2))
        pinsX = []
        pinsY = []

        for coordinates in cells.values():
            xl = coordinates[0]
            xl = xl * imgW / maxX # Normalization
            xl = math.floor(xl)
            xu = math.ceil(coordinates[2] * imgW / maxX)
            yl = math.floor(coordinates[1] * imgH / maxY)
            yu = math.ceil(coordinates[3] * imgH / maxY)

            for i in range(xl, xu+1):
                for j in range(yl, yu+1):
                    data[i,j] += 1
        if display3DPins:
            for pin in pins:
                pinsX.append(math.floor(pin[0] * imgW / maxX))
                pinsY.append(math.floor(pin[1] * imgH / maxY))


        logger.debug("max in data: {}".format(data.max()))

        # https://matplotlib.org/gallery/images_contours_and_fields/pcolor_demo.html

        x, y = np.mgrid[0:imgW+2:1, 0:imgH+2:1]

        if counter == 0:
            ax = axs[0, 0]
        if counter == 1:
            ax = axs[0, 1]
        elif counter == 2:
            ax = axs[1, 0]
        elif counter == 3:
            ax = axs[1, 1]
        ax.set_xlim([0,imgW+2])
        ax.set_ylim([0,imgH+2])
        c = ax.pcolormesh(x, y, data, cmap='Reds', shading='auto', vmin=data.min(), vmax=data.max())
        # ax.plot([10], marker='', color='y')
        if display3DPins:
            ax.scatter(pinsX, pinsY, marker='.', color='y', s=1)
        ax.set_title('Resolution: {}'.format(floor(dimension)))
        ax.axis('equal')
        fig.colorbar(c, ax=ax)
    fig.set_size_inches(11, 9)
    fig.tight_layout()
    plt.savefig('{}_{}_heatmap.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), "_".join(os.getcwd().split(os.sep)[-1].split('_')[2:])), dpi=150)
    plt.show()

def colorizeClusters(clustDir, cells, dimension=1000):
    """
    ClustersInstances.out should be formatted as follow:
    <cluster ID> <instance 1> <...> <instance n>\n

    Parameters
    ----------
    clustDir : str
        folder containing ClustersInstances.out
    cells : {cell name : [x1, y1, x2, y2]}
    """
    imgW = math.floor(dimension)
    imgH = int(imgW * (maxY/maxX))

    data = np.zeros(shape=(imgW+2,imgH+2))

    with open(os.path.join(clustDir,"ClustersInstances.out"), 'r') as f:
        lines = f.readlines()
        for clusterID, line in enumerate(lines):
            line = line.strip()
            for cellName in line.split(' ')[1:]:
                coordinates = cells[cellName]
                xl = math.floor(coordinates[0] * imgW / maxX)
                xu = math.ceil(coordinates[2] * imgW / maxX)
                yl = math.floor(coordinates[1] * imgH / maxY)
                yu = math.ceil(coordinates[3] * imgH / maxY)

                for i in range(xl, xu+1):
                    for j in range(yl, yu+1):
                        data[i,j] = clusterID + 1 # +1 because I want the value 0 to still mean "there is nothing there"

    x, y = np.mgrid[0:imgW+2:1, 0:imgH+2:1]

    fig, ax = plt.subplots()
    ax.set_xlim([0,imgW+2])
    ax.set_ylim([0,imgH+2])
    c = ax.pcolormesh(x, y, data, cmap='nipy_spectral', shading='auto', vmin=data.min(), vmax=data.max())
    ax.set_title('Resolution: {}'.format(floor(dimension)))
    ax.axis('equal')
    fig.colorbar(c, ax=ax)
    fig.tight_layout()
    plt.savefig(os.path.join(clustDir,'{}_{}_clusters_heatmap.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), "_".join(os.getcwd().split(os.sep)[-1].split('_')[2:]))))
    plt.show()


def colorizePartitions(partFile, cells, maxX, maxY, netCutFile, dimension=1000):
    """
    """
    imgW = math.floor(dimension)
    imgH = int(imgW * (maxY/maxX))

    data = np.zeros(shape=(imgW+2,imgH+2))

    partInstances = dict() # { instance name : 0/1}

    with open(partFile, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            cellName = line.split()[0]
            partID = int(line.split()[1])
            partInstances[cellName] = partID
            coordinates = cells[cellName]
            xl = math.floor(coordinates[0] * imgW / maxX)
            xu = math.ceil(coordinates[2] * imgW / maxX)
            yl = math.floor(coordinates[1] * imgH / maxY)
            yu = math.ceil(coordinates[3] * imgH / maxY)

            for i in range(xl, xu+1):
                for j in range(yl, yu+1):
                    data[i,j] = partID + 1 # +1 because I want the value 0 to still mean "there is nothing there"

    netPoints = dict()
    if netCutFile:
        netInstances = dict() # {net name : [instance names]}
        with open(netCutFile, 'r') as f:
            lines = f.readlines()
        for net in lines[0].split(',')[3:]:
            netInstances[net] = list()
        with open("InstancesPerNet.out", 'r') as f:
            lines = f.readlines()
        for line in lines:
            netName = line.split()[0]
            if netName in netInstances.keys():
                netInstances[netName] = line.split()[1:]
        netPoints = dict() # {net name : [ [partition ID, (x, y)], ...] }
        logger.info("Extracting cut net end points")
        with alive_bar(len(netInstances)) as bar:
            for net in netInstances:
                bar()
                netPoints[net] = list()
                for instance in netInstances[net]:
                    coordinates = cells[instance]
                    xl = math.floor(coordinates[0] * imgW / maxX)
                    xu = math.ceil(coordinates[2] * imgW / maxX)
                    yl = math.floor(coordinates[1] * imgH / maxY)
                    yu = math.ceil(coordinates[3] * imgH / maxY)
                    center = (xl + (xu - xl)/2, yl + (yu - yl)/2)
                    netPoints[net].append([partInstances[instance], center])


    x, y = np.mgrid[0:imgW+2:1, 0:imgH+2:1]

    partDir = os.sep.join(partFile.split(os.sep)[:-1])
    designName = "_".join(os.getcwd().split(os.sep)[-1].split('_')[2:])

    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_xlim([0,imgW+2])
    ax.set_ylim([0,imgH+2])
    c = ax.pcolormesh(x, y, data, cmap='binary', shading='auto', vmin=data.min(), vmax=data.max(), zorder=1)

    logger.info("Plotting 3D nets")
    with alive_bar(len(netPoints)) as bar:
        for net in netPoints:
            bar()
            # Ugly patch to ignore clock net
            if not "clk" in net and not "rst" in net and not "clock" in net:
                # logger.debug("Net: {}, len: {}".format(net, len(netPoints[net])))
                points = netPoints[net]
                color = random.choice(list(mcolors.XKCD_COLORS))
                for i in range(len(points)):
                    for j in range(i+1, len(points)):
                        # If points are on different partitions
                        if points[i][0] != points[j][0]:
                            xs = points[i][1][0] # Source
                            xd = points[j][1][0] # Destination
                            ys = points[i][1][1] # Source
                            yd = points[j][1][1] # Destination

                            ax.plot([xs, xd], [ys, yd], linewidth=1, color=color, zorder=10)
    ax.set_title('Resolution: {}, {}'.format(floor(dimension), designName))
    ax.axis('equal')
    fig.colorbar(c, ax=ax)
    fig.tight_layout()
    plt.savefig(os.path.join(partDir,'{}_{}_clusters_heatmap.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), designName)))
    plt.show()



if __name__ == "__main__":
    output_dir = ""
    clustDir = None
    partFile = None
    netCutFile = None
    dimension=300
    display3DPins = False

    args = docopt(__doc__)
    if args["-d"]:
        output_dir = args["-d"]
    if args["-c"]:
        clustDir = args["-c"]
    if args["-p"]:
        partFile = args["-p"]
    if args["-n"]:
        netCutFile = args["-n"]
    if args["-r"]:
        dimension = int(args["-r"])
    if args["--3D"]:
        display3DPins = True



    # Load base config from conf file.
    logging.config.fileConfig('log.conf')
    # Load logger from config
    logger = logging.getLogger('default')
    # Create new file handler
    fh = logging.FileHandler(os.path.join(output_dir, 'heatmap_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.log'))
    # Set a format for the file handler
    fh.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
    # Add the handler to the logger
    logger.addHandler(fh)

    logger.debug(args)

    os.chdir(output_dir)

    if args["-c"]:
        clustDir = os.path.join(os.getcwd(),args["-c"])
    
    logger.info("Working inside {}".format(output_dir))

    logger.info("Seed: {}".format(RANDOM_SEED))

    cells, maxX, maxY, pins = loadDesign(display3DPins)

    if clustDir:
        colorizeClusters(clustDir, cells,dimension)
    elif partFile:
        colorizePartitions(partFile, cells, maxX, maxY, netCutFile,dimension)
    else:
        generateHeatmap(cells, maxX, maxY,dimension, display3DPins, pins)
