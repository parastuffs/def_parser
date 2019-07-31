import math


def EuclideanDistance(a, b):
    """
    Compute the euclidean distance between two points.

    Parameters
    ----------
    a : tuple
        Pair of float (x, y)
    b : tuple
        Pair of float (x, y)

    Returns
    -------
    float
    """
    return math.sqrt( (a[0] - b[0])**2 + (a[1] - b[1])**2 )






##      ##    #####    ######     #########  
###     ##  ##     ##  ##    ##   ##         
## ##   ##  ##     ##  ##     ##  ##         
##  ##  ##  ##     ##  ##     ##  ######     
##   ## ##  ##     ##  ##     ##  ##         
##     ###  ##     ##  ##    ##   ##         
##      ##    #####    ######     #########  

class Node:
    """
    Node of the BST
    """

    def __init__(self, d):
        self.left = None
        self.right = None
        self.data = d

    def insert(self, d):
        """
        Insert the data as a node, left or right.

        Parameters
        ----------
        d : tuple
            Pair of float (x, y)

        Return
        ------
            True if new Node created
            False if the data is already in a node
        """
        if self.data == d:
            return False
        elif d < self.data:
            if self.left:
                return self.left.insert(d)
            else:
                self.left = Node(d)
                return True
        elif d > self.data:
            if self.right:
                return self.right.insert(d)
            else:
                self.right = Node(d)
                return True

    def findClosest(self, d):
        """
        Find the closest Node to given data.
        It returns the closest Node data found.

        Parameter
        ---------
        d : tuple
            Pair of float (x, y)

        Return
        ------
        tuple
            Pair of float (x, y)
        """
        if self.data == d:
            return d
        elif d < self.data:
            if self.left:
                return self.left.findClosest(d)
            else:
                return self.data
        elif d > self.data:
            if self.right:
                return self.right.findClosest(d)
            else:
                return self.data

    def nnsearch(self, p, minDist, bestNode):
        """
        Nearest neighbour search

        TODO Doc
        """
        if self.data == p:
            minDist = 0
            bestNode = self.data
            return minDist, bestNode

        dist = EuclideanDistance(self.data, p)
        if dist < minDist:
            minDist = dist
            bestNode = self.data

        if self.data > p:
            # Check if hypersphere crosses hyperplane
            if ((abs(self.data[0] - p[0]) < dist) or (abs(self.data[1] - p[1]) < dist)) and self.right:
                minDist, bestNode = self.right.nnsearch(p, minDist, bestNode)
            # Explore closer to the point
            if self.left:
                minDist, bestNode = self.left.nnsearch(p, minDist, bestNode)
        elif self.data < p:
            if ((abs(self.data[0] - p[0]) < dist) or (abs(self.data[1] - p[1]) < dist)) and self.left:
                minDist, bestNode = self.left.nnsearch(p, minDist, bestNode)
            # Explore closer to the point
            if self.right:
                minDist, bestNode = self.right.nnsearch(p, minDist, bestNode)

        return minDist, bestNode

    def isLeaf(self):
        """
        Tells if the Node is a leaf in the tree.

        Return
        ------
            True if the Node is a leaf
        """
        return not self.left and not self.right

    def printNodes(self):
        """
        Recursively build an array of node data.

        Return
        ------
        array
        """
        arr = list()
        arr.append(self.data)
        if self.left:
            arr.append(self.left.printNodes())
        if self.right:
            arr.append(self.right.printNodes())
        return arr




########    #######   ##########  
##     ##  ##     ##      ##      
##     ##  ##             ##      
########    #######       ##      
##     ##         ##      ##      
##     ##  ##     ##      ##      
########    #######       ##     

class BST:
    """
    Binary Search Tree implementation for tuples of floats.
    """

    def __init__(self):
        self.root = None

    def insert(self, data):
        """
        Add a node to the bst.
        If the root has not been set yet, this data becomes the root.
        Otherwise, insert it inside the tree using the Node.insert() method.

        Parameters
        ----------
        node : tuple
            Pair of float (x, y)
        """
        if self.root:
            self.root.insert(data)
        else:
            self.root = Node(data)

    def findClosest(self, d):
        """
        Find the closest Node to the given data in the current bst.

        Parameter
        ---------
        d : tuple
            Pair of float (x, y)

        Return
        ------
        tuple of pair of float if the tree has a root
        None otherwise
        """
        if self.root:
            return self.root.findClosest(d)
        else:
            return None

    def nnsearch(self, p):
        """
        TODO Doc
        """
        dist, center = self.root.nnsearch(p, float('inf'), self.root.data)
        return center

    def bstToArray(self):
        """
        [root, [left], [right]] for the simplest tree.
        Each element is the data of the node.

        A more intricate tree could be
            [root, [left1, [left2], [right2, [left3]]], [right1, [left4]]]
        Return
        ------
        array of tuples
        """
        arr = list()
        if self.root:
            arr = self.root.printNodes()
        return arr


def buildBalancedBST(array, bst):
    """
    Recursive function populating a bst in a balanced way.
    There isn't much verification that needs to be done, you can't overflow with an array slice.

    Parameter
    ---------
    array : list()
        Non-balanced array
    """
    if len(array) > 0:
        array.sort()
        mid = int(len(array)/2)
        bst.insert(array[mid])
        buildBalancedBST(array[:mid], bst)
        buildBalancedBST(array[mid+1:], bst)

