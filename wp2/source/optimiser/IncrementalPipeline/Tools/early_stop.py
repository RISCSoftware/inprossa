import gurobipy as gp
from gurobipy import GRB

IMPROVEMENT_THRESHOLD = 0.0001  # 0.01%
MAX_NO_IMPROVE = 1000           # Max allowed checks without improvement

# Use global variables or attach to model for tracking state
last_obj = [None]      # Use list for mutability in closure
no_improve_count = [0]

def stopping_callback(model, where):
    if where == GRB.Callback.MIP:
        current_obj = model.cbGet(GRB.Callback.MIP_OBJBST)

        if current_obj == GRB.INFINITY:
            return  # No feasible solution yet

        if last_obj[0] is None:
            last_obj[0] = current_obj
            return

        rel_diff = abs(current_obj - last_obj[0]) / max(abs(last_obj[0]), 1e-8)

        if rel_diff < IMPROVEMENT_THRESHOLD:
            no_improve_count[0] += 1
        else:
            no_improve_count[0] = 0  # Reset if we see improvement
            last_obj[0] = current_obj

        if no_improve_count[0] >= MAX_NO_IMPROVE:
            print("Stopping: No improvement after 1000 checks.")
            model.terminate()

        # Optional: Also stop based on small relative gap between obj and bound
        bound = model.cbGet(GRB.Callback.MIP_OBJBND)
        if abs(current_obj) > 1e-6 and abs(current_obj - bound) / abs(current_obj) < IMPROVEMENT_THRESHOLD:
            print("Stopping: Relative gap below 0.01%.")
            model.terminate()