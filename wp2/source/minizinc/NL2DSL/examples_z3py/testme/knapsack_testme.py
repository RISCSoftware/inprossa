from z3 import *

# Constants: item values and weights
item_names = ["scissor", "book", "laptop", "phone", "ruler", "pen"]

item_values = {
    "scissor": 15,
    "book": 50,
    "laptop": 80,
    "phone": 80,
    "ruler": 20,
    "pen": 25
}

item_weights = {
    "scissor": 12,
    "book": 70,
    "laptop": 100,
    "phone": 20,
    "ruler": 12,
    "pen": 5
}

# Decision variables: whether each item is chosen
item_chosen = {name: Bool(name) for name in item_names}

# Constant: maximum bag capacity
max_capacity = 110

# Create the Z3 optimizer
opt = Optimize()

# Objective: maximize total value of selected items
total_value = Sum([
    If(item_chosen[name], item_values[name], 0)
    for name in item_names
])

opt.maximize(total_value)

def add_constraints(opt, item_chosen, item_weights, max_capacity):
    # Constraint: total weight ≤ max_capacity
    total_weight = Sum([
        If(item_chosen[name], item_weights[name], 0)
        for name in item_chosen
    ])
    opt.add(total_weight <= max_capacity)

    # check equivalence
    equivSolver = Solver()

    constraints = []
    phi = And(total_weight <= max_capacity)

    z = Int("z")
    #constraints.append(z >= 0)
    constraints.append(z == Sum([item_chosen[i] * item_values[i] for i in item_values.keys()]))
    constraints.append(Sum([item_chosen[i] * item_weights[i] for i in item_weights.keys()]) <= max_capacity)
    psi = And(constraints)

    equivSolver.add(Or(And(phi, Not(psi)), And(Not(phi), psi)))  # Negation of equivalence

    if equivSolver.check() == unsat:
        print("✅ The two constraint sets are logically equivalent.")
    else:
        print("❌ They are NOT logically equivalent.")
        print("Counterexample:")
        print(equivSolver.model())

# Add the constraints to the optimizer
add_constraints(opt, item_chosen, item_weights, max_capacity)

if opt.check() == sat:
    model = opt.model()
    chosen_items = [name for name in item_names if model.eval(item_chosen[name])]
    total_val = sum(item_values[name] for name in chosen_items)
    total_wgt = sum(item_weights[name] for name in chosen_items)

    print("Chosen items:", chosen_items)
    print("Total value:", total_val)
    print("Total weight:", total_wgt)
else:
    print("No solution found.")