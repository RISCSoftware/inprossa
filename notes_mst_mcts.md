- Selection: Start from root node R and select successive child nodes (given selection rules) until you reach a node L that has at least one unvisited child. Such a node L is called a leaf node.
- Expansion: Select an unvisited child C of L
- Simulation: Complete random playout of C
- Backpropagation:  Use the result of the playout to update information in the nodes on the path from C to R.

Selection rules:
