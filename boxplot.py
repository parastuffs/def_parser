"""
Usage:
    boxplot.py   FILE
    boxplot.py (--help|-h)

Options:
    FILE                    Rent's stats file location
    -h --help               Print this help
"""


import matplotlib.pyplot as plt
import numpy as np
import csv
import operator
import math
from docopt import docopt

args = docopt(__doc__)
if args["FILE"]:
    rentFile = args["FILE"]


pos = list()
data = list()
data_raw = list()

x = list()
y = list()
median = list()

pos_log = list()
median_log = list()

points = list()
points_log = list()

with open(rentFile, 'r') as f:
    reader = csv.reader(f)
    next(reader, None)  # skip the headers

    # Map int to csv lines
    for row in reader:
        row = map(int, row)
        data_raw.append(row)

    # Sort data based on the first element of each row
    data_raw.sort(key=lambda x : x[0])
    
    for row in data_raw:

        # Get x value (number of gates)
        pos.append(row[0])
        pos_log.append(math.log(row[0], 10))

        # BOXPLOT
        data.append(row[1:])

        # SCATTERPLOT
        for i in range(len(row[1:])):
            x.append(row[0])
        for e in row[1:]:
            y.append(e)

        # Find median
        median.append(np.median(row[1:]))
        median_log.append(math.log(median[-1], 10))
        # try:
        #   median_log.append(math.log(median[-1], 10))
        # except ValueError:
        #   print row[1:]
        #   print median[-1]

fit = np.polyfit(pos_log, median_log, 1)
fit_fn = np.poly1d(fit)
# print fit
# print fit_fn

y_rent = [math.pow(10,fit[1])*math.pow(i, fit[0]) for i in pos]

reg_legend = "y = {} * x^{}".format(math.pow(10,fit[1]), fit[0])

plt.plot(pos, median, 'yo')
# plt.plot(pos_log, fit_fn(pos_log), 'g')
reg_line, = plt.plot(pos, y_rent, 'r', label=reg_legend)

# plt.boxplot(data, positions=pos)
plt.scatter(x, y)

plt.xscale("log")
plt.yscale("log")

plt.legend(handles=[reg_line])

plt.show()
