#!/usr/bin/python -u
# -*- coding: latin-1 -*-
#
# Traveling Salesman Problem, integer programming model in Z3
#
# From GLPK:s example tsp.mod
# """
# TSP, Traveling Salesman Problem
#
# Written in GNU MathProg by Andrew Makhorin <mao@mai2.rcnet.ru> */
#
# The Traveling Salesman Problem (TSP) is stated as follows.
# Let a directed graph G = (V, E) be given, where V = {1, ..., n} is
# a set of nodes, E <= V x V is a set of arcs. Let also each arc
# e = (i,j) be assigned a number c[i,j], which is the length of the
# arc e. The problem is to find a closed path of minimal length going
# through each node of G exactly once.
# """

#
# This Z3 model was written by Hakan Kjellerstrand (hakank@gmail.com)
# See also my Z3 page: http://hakank.org/z3/
#
from z3_utils_hakank import *

sol = SolverFor("QF_LIA")
# sol = SolverFor("LIA")
# sol = Solver()

#
# data
#

# """
# These data correspond to the symmetric instance ulysses16 from:
# Reinelt, G.: TSPLIB - A travelling salesman problem library.
# ORSA-Journal of the Computing 3 (1991) 376-84;
# http://elib.zib.de/pub/Packages/mp-testdata/tsp/tsplib
#
# The optimal solution is 6859
# """

n = 16
num_edges = 240

# This is a matrix of (n-1) x (n-1) which excludes the main diagonal (i,i)
#
E = [ [i,j] for i in range(n) for j in range(n) if i != j ]

# for i in range(num_edges):
#   print(E[i])

c=[
509,501,312,1019,736,656,60,1039,726,2314,479,448,479,619,150,509,126,474,1526,
1226,1133,532,1449,1122,2789,958,941,978,1127,542,501,126,541,1516,1184,1084,536,
1371,1045,2728,913,904,946,1115,499,312,474,541,1157,980,919,271,1333,1029,2553,
751,704,720,783,455,1019,1526,1516,1157,478,583,996,858,855,1504,677,651,600,401,
1033,736,1226,1184,980,478,115,740,470,379,1581,271,289,261,308,687,656,1133,1084,
919,583,115,667,455,288,1661,177,216,207,343,592,60,532,536,271,996,740,667,1066,759,
2320,493,454,479,598,206,1039,1449,1371,1333,858,470,455,1066,328,1387,591,650,656,
776,933,726,1122,1045,1029,855,379,288,759,328,1697,333,400,427,622,610,2314,2789,
2728,2553,1504,1581,1661,2320,1387,1697,1838,1868,1841,1789,2248,479,958,913,
751,677,271,177,493,591,333,1838,68,105,336,417,448,941,904,704,651,289,216,454,
650,400,1868,68,52,287,406,479,978,946,720,600,261,207,479,656,427,1841,105,52,
237,449,619,1127,1115,783,401,308,343,598,776,622,1789,336,287,237,636,150,542,499,
455,1033,687,592,206,933,610,2248,417,406,449,636
]

#
# variables
#

# x[i,j] = 1 means that the salesman goes from node i to node j
x = makeIntVector(sol,"x",num_edges,0,1)

# y[i,j] is the number of cars, which the salesman has after leaving
# node i and before entering node j; in terms of the network analysis,
# y[i,j] is a flow through arc (i,j)
# array[1..num_edges] of var int: y;
y = makeIntVector(sol,"y",num_edges,0,n)

# the objective is to make the path length as small as possible
total = makeIntVar(sol,"total",0,9999)

#
# constraints
#

sol.add(total == Sum([(c[i] * x[i]) for i in range(num_edges)]))

# the salesman leaves each node i exactly once
for i in range(n):
  sol.add(Sum([x[k] for k in range(num_edges) if E[k][0] == i]) == 1)

# the salesman enters each node j exactly once
for j in range(n):
  sol.add(Sum([x[k] for k in range(num_edges) if E[k][1] == j]) == 1)


# """
# Constraints above are not sufficient to describe valid tours, so we
# need to add constraints to eliminate subtours, i.e. tours which have
# disconnected components. Although there are many known ways to do
# that, I invented yet another way. The general idea is the following.
# Let the salesman sells, say, cars, starting the travel from node 1,
# where he has n cars. If we require the salesman to sell exactly one
# car in each node, he will need to go through all nodes to satisfy
# this requirement, thus, all subtours will be eliminated.
#

# if arc (i,j) does not belong to the salesman's tour, its capacity
# must be zero; it is obvious that on leaving a node, it is sufficient
# to have not more than n-1 cars
# """
for k in range(num_edges):
   sol.add(y[k] >= 0)
   sol.add(y[k] <= (n-1) * x[k])

# node[i] is a conservation constraint for node i
for i in range(n):
   # summary flow into node i through all ingoing arcs
   sol.add(
      (
      Sum([y[k] for k in range(num_edges) if E[k][1] == i])
      # plus n cars which the salesman has at starting node
      + If(i == 0, n, 0)
      )
   == # must be equal to
   # summary flow from node i through all outgoing arcs
   (
   Sum([y[k] for k in range(num_edges) if E[k][0] == i])
   # plus one car which the salesman sells at node i
   + 1
   ))

print("solve")
num_solutions = 0
while sol.check() == sat:
  num_solutions += 1
  mod = sol.model()
  print("total:", mod.eval(total))
  print("x :", [mod.eval(x[i]) for i in range(num_edges)])
  print("y :", [mod.eval(y[i]) for i in range(num_edges)])
  print()
  getLessSolution(sol,mod,total)

print("num_solutions:", num_solutions)