"""
Usage:
    heatmap.py (-d <dir>) [-c <dir>]
    heatmap.py (--help|-h)

Options:
    -d <path>   Path to design folder
    -c <dir>    Sub dir from <path> to a folder containing ClustersInstances.out
    -h --help   Print this help
"""


from __future__ import division # http://stackoverflow.com/questions/1267869/how-can-i-force-division-to-be-floating-point-division-keeps-rounding-down-to-0
from PIL import Image
from math import *
import copy
import locale
import os
import shutil
import datetime
import errno
import random
from docopt import docopt
import logging, logging.config
import numpy as np
import sys
import matplotlib.pyplot as plt
import bst
import statistics
import math
from alive_progress import alive_bar
from Classes.Cluster import *
from Classes.Gate import *
from Classes.Net import *
from Classes.Pin import *
from Classes.Port import *
from Classes.StdCell import *
from Classes.GatePin import *
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

RANDOM_SEED = 0 # Set to 0 if no seed is used, otherwise set to seed value.


def loadDesign():
    """
    CellSizes.out:
        <cell name> <width [float]> <height [float]>
    CellCoord.out:
        <net name>, <cell name>, <x [float]>, <y [float]>

    Return
    ------
    cells : {}
    maxX : float
    maxY : float
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
            cells[cellName].extend([cells[cellName][0] + float(line.split(' ')[1]), cells[cellName][1] + float(line.split(' ')[2])])
            maxX = max(maxX, cells[cellName][2])
            maxY = max(maxY, cells[cellName][3])
    return cells, maxX, maxY

def generateHeatmap(cells, maxX, maxY, dimension=300):
    """
    Parameters
    ----------
    cells : {cell name : [x1, y1, x2, y2]}
    maxX : float
    maxY : float
    """



    fig, axs = plt.subplots(2,2)

    for counter, dimension in enumerate([dimension/10, dimension/5, dimension/2, dimension]):
        imgW = math.floor(dimension)
        imgH = int(imgW * (maxY/maxX))

        data = np.zeros(shape=(imgW+2,imgH+2))

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
        ax.set_title('Resolution: {}'.format(floor(dimension)))
        ax.axis('equal')
        fig.colorbar(c, ax=ax)
    fig.tight_layout()
    plt.savefig('{}_{}_heatmap.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), "_".join(os.getcwd().split(os.sep)[-1].split('_')[2:])))
    plt.show()

def clororizeClusters(clustDir, cells, dimension=1000):
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


if __name__ == "__main__":
    output_dir = ""
    clustDir = None

    args = docopt(__doc__)
    if args["-d"]:
        output_dir = args["-d"]
    if args["-c"]:
        clustDir = args["-c"]

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

    cells, maxX, maxY = loadDesign()

    if clustDir:
        clororizeClusters(clustDir, cells)
    else:
        generateHeatmap(cells, maxX, maxY)