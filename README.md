# DEF parser and clustering

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