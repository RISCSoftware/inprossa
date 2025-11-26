from pandas.core.arrays.interval import IntervalSide

str ="""
from z3 import *

# Problem parameters
values = [60, 100, 120]
weights = [10, 20, 30]
capacity = 50
n = len(values)

# Z3 variables
x = [Bool(f"x_{i}") for i in range(n)]

# Solver
s = Optimize()

# Add capacity constraint
s.add(Sum([If(x[i], weights[i], 0) for i in range(n)]) <= capacity)

# Maximize value
s.maximize(Sum([If(x[i], values[i], 0) for i in range(n)]))

# Check and print solution
if s.check() == sat:
    m = s.model()
    selected = [i for i in range(n) if m.evaluate(x[i])]
    print("Selected items:", selected)
else:
    print("No solution found.")
"""
#exec(str)

from z3 import Int, And, Sum, Optimize, sat

# Item data using constants
items = {
    "scissor": (15, 12),
    "book": (50, 70),
    "laptop": (80, 100),
    "phone": (80, 20),
    "ruler": (20, 12),
    "pen": (25, 5),
}
MAX_WEIGHT = 110

# Decision variables and constraints
item_vars = {name: Int(name) for name in items}
constraints = [And(0 <= var, var <= 1) for var in item_vars.values()]

# Total weight and value expressions using Sum
total_value = Sum([var * val for (var, (_, val)) in zip(item_vars.values(), items.values())])
total_weight = Sum([var * wgt for (var, (val, wgt)) in zip(item_vars.values(), items.values())])

# Add weight constraint
constraints.append(total_weight <= MAX_WEIGHT)

# Setup solver
opt = Optimize()
opt.add(constraints)
opt.maximize(total_value)

# Output results
if opt.check() == sat:
    model = opt.model()
    print("Optimal Solution Found!")
    print(f"Total Value: {model.evaluate(total_value)}")
    print(f"Total Weight: {model.evaluate(total_weight)}")
    print("Items in the Bag:")
    for name, (v, w) in items.items():
        if model[item_vars[name]] == 1:
            print(f"- {name.capitalize()}: Value={v}, Weight={w}")
else:
    print("No solution found.")