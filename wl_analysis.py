import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import os
import datetime
import math

TITLE = list()
WLNET_F = list()
AGW = list()
HPL = list()
MGW = list()

TITLE.append("Boomcore 2020, post-place, bufffer-less, in7")
WLNET_F.append("/home/para/dev/def_parser/2020-12-04_09-38-26_boomcore-2020-pp-bl_digest/WLnets.out")
AGW.append(0.205)
HPL.append(111.636+111.616)
MGW.append(0.084)

TITLE.append("Boomcore 2020 3D, post-place, bufffer-less, in7")
WLNET_F.append("/home/para/Documents/ULB/phd/experiments/2020-12/Boomcore-2020-pp-bl/Gate-Level/3D/WLnets_TOP-BOT-merged_3D.out")
AGW.append((69552*0.24692874396135264 + 91449*0.205003116491159)/(69552+91449)) # (gates_bot * agw_bot + gates_top * agw_top) / gates_tot
HPL.append(max([76.5660+76.2880,74.8860+74.5600])) # [Bottom, Top]
MGW.append(0.084)

TITLE.append("SPC 2020, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2020-09-29_20-59-49_spc-2020_metal/WLnets.out")
AGW.append(0.235) # SPC 2020
HPL.append(166.488+284.032)
MGW.append(0.084)

TITLE.append("SPC 2020, post-route, buffer-less, in7")
WLNET_F.append("/home/para/dev/def_parser/2020-07-30_23-07-07_spc-bufferless-2020_kmeans-geometric/WLnets.out")
AGW.append(0.24228685394212)
HPL.append(166.488+284.032)
MGW.append(0.084)

TITLE.append("Boomcore 2020, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2020-11-27_10-54-30_boomcore-2020_digest/WLnets.out")
AGW.append(0.205) # Boomcore 2020
HPL.append(111.636+111.616)
MGW.append(0.084)

# TITLE.append("MSP430, post-route, with buffers, osu018")
# WLNET_F.append("/home/para/dev/def_parser/2020-06-09_15-55-48_msp430_digest/WLnets.out")
# AGW.append(3.6) # MSP430
# HPL.append(111.636+111.616)
# MGW.append()

TITLE.append("armm0, post-route, with buffers, gsclib045")
WLNET_F.append("/home/para/dev/def_parser/2019-10-15_00-48-01_armm0_digest/WLnets.out")
AGW.append(1.4747364722417426)
HPL.append(144.84+143.64)
MGW.append(0.4)

TITLE.append("LDPC, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2019-07-05_17-11-24_ldpc_digest/WLnets.out")
AGW.append(0.238) # LDPC
HPL.append(57.582+57.472)
MGW.append(0.084)

TITLE.append("LDPC 4x4 Fully Connected, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2019-03-12_11-20-44_ldpc-4x4_digest/WLnets.out")
AGW.append(0.249619997055) # LDPC 4x4 fully connected
HPL.append(325.248+324.928)
MGW.append(0.084)

TITLE.append("LDPC 4x4 Serial, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2019-07-09_15-09-13_ldpc-4x4-serial_digest/WLnets.out")
AGW.append(0.246599099242) # LDPC 4x4 Serial
HPL.append(238.938+238.912)
MGW.append(0.084)

TITLE.append("CCX, post-route, with buffers, CDN45")
WLNET_F.append("/home/para/dev/def_parser/2019-07-09_15-07-10_ccx_digest/WLnets.out")
AGW.append(1.40812530076)
HPL.append(801.486+391.104)
MGW.append(0.378)

TITLE.append("SPC, post-route, with buffers, CDN45")
WLNET_F.append("/home/para/dev/def_parser/2019-07-09_15-07-19_spc_digest/WLnets.out")
AGW.append(1.42219185541)
HPL.append(729.036+1243.872)
MGW.append(0.378)

TITLE.append("flipr, post-route, with buffers, in7")
WLNET_F.append("/home/para/dev/def_parser/2019-07-09_15-06-12_flipr_digest/WLnets.out")
AGW.append(0.21603400019)
HPL.append(121.38+121.216)
MGW.append(0.084)

TITLE.append("SPC, post-place, 3D MoL, in7")
WLNET_F.append("/home/para/Documents/ULB/phd/experiments/2020-12/spcDATE2020 stats/MoL/WLnets_3D_merged_post-place.out")
AGW.append(0.235)
HPL.append(max([2*math.sqrt(14495.685), 2*math.sqrt(20987.091)])) # [Bottom, Top]
MGW.append(0.084)


for i in range(len(WLNET_F)):
	with open(WLNET_F[i], 'r') as f:
		lines = f.readlines()

	wirelengths = list()
	for line in lines[1:]:
		wl = float(line.split()[2])
		if wl > 0:
			wirelengths.append(wl)
	wirelengthsNorm = [x/MGW[i] for x in wirelengths]

	sortedWL = np.sort(wirelengthsNorm)
	# Note: numpy.cumsum would also do the trick
	cumulWL = [sortedWL[0]]
	for j in range(1,sortedWL.size):
		cumulWL.append(cumulWL[-1] + sortedWL[j])
	maxCumulWL = max(cumulWL)
	cumulWLNorm = [100*x/maxCumulWL for x in cumulWL]
	# Number of nets
	netsPlot, = plt.step(sortedWL, np.linspace(0,100,sortedWL.size))
	netsPlot.set_label("Nets, cumulative, {}".format(TITLE[i]))
	# WL cumulative plot
	wlPlot, = plt.step(sortedWL, cumulWLNorm)
	wlPlot.set_label("Wirelength, cumulative, {}".format(TITLE[i]))

plt.xscale("log")
plt.title("Wirelength distribution")
plt.legend()
plt.ylabel("%")
plt.xlabel("Wirelength, normalized on the AGW")
plt.yticks(np.arange(0, 101, step=20))
ax = plt.gca()
ax.yaxis.set_minor_locator(MultipleLocator(5))
plt.grid(True, which='both')
os.chdir("/home/para/Documents/ULB/phd/experiments/2020-12/")
# plt.savefig('{}_wl-distribution_{}.pdf'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), TITLE.replace(", ", "_").replace(" ","-")))
# plt.savefig('{}_wl-distribution_{}.png'.format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), TITLE.replace(", ", "_").replace(" ","-")))
plt.show()