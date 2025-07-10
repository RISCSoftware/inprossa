from gurobipy import Model, GRB
from cut import cut
from filter import filter
from check import ensure_correct_beam
from reorder import reorder
import config

model = Model("BeamCutting")
# Configure the model
model.setParam("TimeLimit", 10)     # Fallback time limit
model.setParam("MIPGap", 0.05)      # Accept solutions within 5% gap

cut_lengths = cut(model,
                  config.input_board,
                  config.n_cuts,
                  config.n_intervals)
filtered = filter(model,
                  list(cut_lengths.values()),
                  config.min_length,
                  config.max_length,
                  id="filtered")
reordered1 = reorder(model,
                     list(filtered.values()),
                     config.beam_length,
                     id="reordered1")
reordered2 = reorder(model,
                     list(reordered1.values()),
                     config.beam_length,
                     id="reordered2")
# reordered3 = reorder(model,
#                      list(reordered2.values()),
#                      config.beam_length,
#                      id="reordered3")
ensure_correct_beam(list(reordered2.values()),
                    config.n_layers,
                    config.n_layers_per_beam,
                    config.pieces_per_layer,
                    config.beam_length,
                    model,
                    config.global_danger)

model.optimize()

if model.Status == 4:  # GRB.INFEASIBLE
    print("Model is infeasible. Computing IIS...")
    model.computeIIS()
    model.write("infeasible.ilp")  # Optional: view this in Gurobi IDE or a text editor

    for c in model.getConstrs():
        if c.IISConstr:
            print(f"Infeasible constraint: {c.ConstrName}")


print("\nCut positions:")
for v in model.getVars():
    if v.VarName.startswith("cut_vars") and abs(v.X) > 1e-6:
        print(f"{v.VarName}: {v.X:.2f}")

print("\nFiltering decision variables:")
for v in model.getVars():
    if v.VarName.startswith("b") and v.X > 0.5:
        print(f"{v.VarName}: {v.X:.2f}")

print("\nReordered pieces:")
for v in model.getVars():
    if v.VarName.startswith("output_reordered") and abs(v.X) > 1e-6:
        print(f"{v.VarName}: {v.X:.2f}")

# It would be great to have:
# -Every two seconds new information is given
# - Start with the smallest amount of information and solve it
# - Adding more information every time it's solved while keeping the solution
# - When it's time to execute one of the solutions send the order. Actualise the solution and keep solving starting from that solution.