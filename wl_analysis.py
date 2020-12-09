import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# WLNET_F = "/home/para/dev/def_parser/2020-12-04_09-38-26_boomcore-2020-pp-bl_digest/WLnets.out"
# WLNET_F = "/home/para/dev/def_parser/2020-09-29_20-59-49_spc-2020_metal/WLnets.out"
# WLNET_F = "/home/para/dev/def_parser/2020-11-27_10-54-30_boomcore-2020_digest/WLnets.out"
# WLNET_F = "/home/para/dev/def_parser/2020-06-09_15-55-48_msp430_digest/WLnets.out"
WLNET_F = "/home/para/dev/def_parser/2019-07-05_17-11-24_ldpc_digest/WLnets.out"
# AGW = 0.205 # Boomcore 2020
# AGW = 0.235 # SPC 2020
# AGW = 3.6 # MSP430
AGW = 0.238 # LDPC

if __name__ == "__main__":

	with open(WLNET_F, 'r') as f:
		lines = f.readlines()

	wirelengths = list()
	for line in lines[1:]:
		wirelengths.append(float(line.split()[2]))
	wirelengthsNorm = [i/AGW for i in wirelengths]

	sortedWL = np.sort(wirelengthsNorm)
	# Note: numpy.cumsum would also do the trick
	cumulWL = [sortedWL[0]]
	for i in range(1,sortedWL.size):
		cumulWL.append(cumulWL[-1] + sortedWL[i])
	maxCumulWL = max(cumulWL)
	cumulWLNorm = [100*i/maxCumulWL for i in cumulWL]
	plt.xscale("log")
	# Number of nets
	netsPlot, = plt.step(sortedWL, np.linspace(0,100,sortedWL.size))
	netsPlot.set_label("Nets, cumulative")
	# WL cumulative plot
	wlPlot, = plt.step(sortedWL, cumulWLNorm)
	wlPlot.set_label("Wirelength, cumulative")
	plt.title("Wirelength distribution for Boomcore 2020, post-place, bufffer-less")
	plt.legend()
	plt.ylabel("%")
	plt.xlabel("Wirelength, normalized on the AGW ({})".format(AGW))
	plt.yticks(np.arange(0, 101, step=20))
	plt.axes().yaxis.set_minor_locator(MultipleLocator(5))
	plt.grid(True, which='both')
	plt.show()