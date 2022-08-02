# DEF parser and clustering

```
Usage:
    def_parser.py   [--design=DESIGN] [--clust-meth=METHOD] [--seed=<seed>] [CLUSTER_AMOUNT ...]
                    [--manhattanwl] [--mmstwl] [--cnwl] [--bb=<method>]
                    [--deffile=DEF] [--udm=VALUE] [--leftech=TECH] [--segments]
                    [--bold]
    def_parser.py (--help|-h)
    def_parser.py   [--design=DESIGN] (--digest) [--manhattanwl] [--mmstwl] [--cnwl] [--bb=<method>]
                    [--deffile=DEF] [--udm=VALUE] [--leftech=TECH] [--segments]

Options:
    --design=DESIGN         Design to cluster. One amongst ldpc, ldpc-2020, flipr, boomcore, boomcore-2020, spc,
                            spc-2020, spc-bufferless-2020, ccx, ccx-in3, ccx-in3-du10, ccx-in3-du85,
                            ldpc-4x4-serial, ldpc-4x4, 
                            ldpc-4x4-serial-2022, ldpc-4x4-serial-delBuffPy-2022, ldpc-4x4-serial-delBuff-2022, ldpc-4x4-serial-pre-CTS-2022,
                            ldpc-4x4-full-2022, ldpc-4x4-full-noFE-2022, ldpc-4x4-full-delBUFF-2022, 
                            ldpc-4x4-full-preCTS-2022, ldpc-4x4-full-delBuffPy-2022,
                            smallboom, armm0,msp430, megaboom-pp-bl, megaboom-pp-bt, 
                            mempool-tile-bl, mempool-tile-bt, mempool-group-bl, mempool-group-FP-noFE,
                            mempool-tile-post-FP, mempool-tile-post-FP-noFE, 
                            mempool-tile-pp, mempool-tile-pp-noFE.
    --clust-meth=METHOD     Clustering method to use. One amongst progressive-wl, random,
                            Naive_Geometric, hierarchical-geometric, kmeans-geometric, kmeans-random, onetoone.
                            or metal. [default: random]
    --seed=<seed>           RNG seed
    CLUSTER_AMOUNT ...      Number of clusters to build. Multiple arguments allowed.
    --manhattanwl           Compute nets wirelength as Manhattan distance.
    --mmstwl                Compute nets wirelength as MMST (Mixed Minimal Steiner Tree).
    --cnwl                  Compute nets wirelength as Closest Neighbourg (slower, but more accurate).
    --bb=<method>           Bounding box computation method: cell or pin.
    --digest                Print design's info and exit.
    --deffile=DEF           Path to DEF file, superseded by --design.
    --udm=VALUE             UNITS DISTANCE MICRONS, e.g. 10000, superseded by --design
    --leftech=TECH          LEF tech used, e.g. 7nm, superseded by --design
    --segments              Compute the Manhattan segment length of each net into WLnets_wegments.out
    --bold                  Suppress the clustering sanity checks
    -h --help               Print this help
```

## Input files

### DEF
This script needs a fully placed and routed design as a DEF file.

### LEF
Technology file, needed for the geometry and names of the standard cells.

## Output files

### CellCoord.out
Each line is ```<net name>, <instance name>, <x coordinate [float]>, <y coordinate [float]>```.

### InstancesPerNet.out
Each line is ```<net name> <instance name 1> <...> <instance name n>```.

### Nets.out
Each line is ```<net name>```.

### WLnets.out
Header: ```NET NUM_PINS LENGTH```

Then each line is ```<net name> <number of pins [integer]> <length in µm [float]>```.

### Design_net_wl.csv
The nets are first sorted based on their length.

Header: ```Net_name net_wire_length cumulated_wire_length %_of_nets```.

- Column 1: name of the net
- Column 2: length of the net in µm [float]
- Column 3: Cumulated total wire length in µm of the nets so far. This should be
equal to the design total wire length for the last line.
- Column 4: Percentage of the total amount of nets so far. This should be equal
to 100% for the last line.

### Clusters.out
Each line: ```<cluster name>```

In all the custom clustering methods, the cluster name is its ID, starting at 0
then incrementing by 1.

### ClustersArea.out
Header: ```Name Type InstCount Boundary Area```

- Column 1: ```<cluster name>```, same as in ```Clusters.out```
- Column 2: Type of cluster, ```exclusive``` by default.
- Column 3: Amount of instances in the cluster [integer]
- Column 4: Coordinates of the cluster's bottom left corner, ```(<x coordinate
	[float]>,<y coordinate [float]>)```
- Column 5: Coordinates of the cluster's top right corner, ```(<x coordinate
	[float]>,<y coordinate [float]>)```
Columns 4 and 5 only make sense if the cluster is rectangular shaped.
- Column 6: area of the cluster in µm2 [float]

### ClustersInstances.out
Each line: ```<cluster name> <instance name 1> <...> <instance name n>```.
