"""
This module provides functionality to warm start a new model
with the parameters of a previous model.
"""
from IncrementalPipeline.Tools.rewrite_variables_names import rewrite_variable_name


def warm_start(new_model, previous_model, machine_changes=None):
    previous_vars = previous_model.getVars()

    for var in previous_vars:
        new_var_name = rewrite_variable_name(var.VarName, machine_changes)
        warm_start_vars_with_same_name(new_model, var.X, new_var_name)


def get_vars_by_name(model, name):
    return [v for v in model.getVars() if v.VarName == name]


def warm_start_vars_with_same_name(new_model, var_value, var_name):
    """
    Update variables in the model with the same name as the given variable.

    :param model: Gurobi model to update.
    :param var: Variable from a previous model to use for updating.
    """

    same_name_vars = get_vars_by_name(new_model, var_name)
    if len(same_name_vars) > 1:
        # Give warning
        # print(f"Warning: Multiple variables with the name {var_name} ",
        #       "found in the new model.")
        pass
    elif len(same_name_vars) == 0:
        # Give warning
        # print(f"Warning: No variable with the name {var_name} ",
        #       "found in the new model.")
        pass
    else:
        # Set the start value of the variable in the new model
        for same_name_var in same_name_vars:
            same_name_var.start = var_value
