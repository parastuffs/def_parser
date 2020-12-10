import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import os
import datetime

# TITLE = "Boomcore 2020, post-place, bufffer-less, in7"
# WLNET_F = "/home/para/dev/def_parser/2020-12-04_09-38-26_boomcore-2020-pp-bl_digest/WLnets.out"
# AGW = 0.205 # Boomcore 2020

# TITLE = "Boomcore 2020 3D, post-place, bufffer-less, in7"
# WLNET_F = "/home/para/Documents/ULB/phd/experiments/2020-12/Boomcore-2020-pp-bl/Gate-Level/3D/WLnets_TOP-BOT-merged_3D.out"
# AGW = (69552*0.24692874396135264 + 91449*0.205003116491159)/(69552+91449) # (gates_bot * agw_bot + gates_top * agw_top) / gates_tot

# TITLE = "SPC 2020, post-route, with buffers, in7"
# WLNET_F = "/home/para/dev/def_parser/2020-09-29_20-59-49_spc-2020_metal/WLnets.out"
# AGW = 0.235 # SPC 2020

# TITLE = "SPC 2020, post-route, buffer-less, in7"
# WLNET_F = "/home/para/dev/def_parser/2020-07-30_23-07-07_spc-bufferless-2020_kmeans-geometric/WLnets.out"
# AGW = 0.24228685394212

# TITLE = "Boomcore 2020, post-route, with buffers, in7"
# WLNET_F = "/home/para/dev/def_parser/2020-11-27_10-54-30_boomcore-2020_digest/WLnets.out"
# AGW = 0.205 # Boomcore 2020

# TITLE = "MSP430, post-route, with buffers, osu018"
# WLNET_F = "/home/para/dev/def_parser/2020-06-09_15-55-48_msp430_digest/WLnets.out"
# AGW = 3.6 # MSP430

# TITLE = "armm0, post-route, with buffers, gsclib045"
# WLNET_F = "/home/para/dev/def_parser/2019-10-15_00-48-01_armm0_digest/WLnets.out"
# AGW = 1.4747364722417426

# TITLE = "LDPC, post-route, with buffers, in7"
# WLNET_F = "/home/para/dev/def_parser/2019-07-05_17-11-24_ldpc_digest/WLnets.out"
# AGW = 0.238 # LDPC

# TITLE = "LDPC 4x4 Fully Connected, post-route, with buffers, in7"
# WLNET_F = "/home/para/dev/def_parser/2019-03-12_11-20-44_ldpc-4x4_digest/WLnets.out"
# AGW = 0.249619997055 # LDPC 4x4 fully connected

# TITLE = "LDPC 4x4 Serial, post-route, with buffers, in7"
# WLNET_F = "/home/para/dev/def_parser/2019-07-09_15-09-13_ldpc-4x4-serial_digest/WLnets.out"
# AGW = 0.246599099242 # LDPC 4x4 Serial

# TITLE = "CCX, post-route, with buffers, CDN45"
# WLNET_F = "/home/para/dev/def_parser/2019-07-09_15-07-10_ccx_digest/WLnets.out"
# AGW = 1.40812530076

# TITLE = "SPC, post-route, with buffers, CDN45"
# WLNET_F = "/home/para/dev/def_parser/2019-07-09_15-07-19_spc_digest/WLnets.out"
# AGW = 1.42219185541

TITLE = "flipr, post-route, with buffers, in7"
WLNET_F = "/home/para/dev/def_parser/2019-07-09_15-06-12_flipr_digest/WLnets.out"
AGW = 0.21603400019


if __name__ == "__main__":

	with open(WLNET_F, 'r') as f:
		lines = f.readlines()

	wirelengths = list()
	for line in lines[1:]:
		wl = float(line.split()[2])
		if wl > 0:
			wirelengths.append(wl)
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
	plt.title("Wirelength distribution for {}".format(TITLE))
	plt.legend()
	plt.ylabel("%")
	plt.xlabel("Wirelength, normalized on the AGW ({})".format(AGW))
	plt.yticks(np.arange(0, 101, step=20))
	plt.axes().yaxis.set_minor_locator(MultipleLocator(5))
	plt.grid(True, which='both')
	os.chdir("/home/para/Documents/ULB/phd/experiments/2020-12/")
	plt.savefig('{}_wl-distribution_{}.pdf'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), TITLE.replace(", ", "_").replace(" ","-")))
	plt.savefig('{}_wl-distribution_{}.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), TITLE.replace(", ", "_").replace(" ","-")))
	# plt.show()