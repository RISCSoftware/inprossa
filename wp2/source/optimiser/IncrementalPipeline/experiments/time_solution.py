
from IncrementalPipeline.configs.default_pipeline import pipeline
from gurobipy import Model
from time import time
from IncrementalPipeline.Tools.early_stop import stopping_callback
from IncrementalPipeline.Tools.warm_start import warm_start


def time_solution(input_list, warm_start_model=None):
    new_model = Model()
    pipeline.intermediate_lists[0] = input_list
    pipeline.impose_conditions(new_model)
    if warm_start_model is not None:
        # Warm start the machine
        warm_start(new_model, warm_start_model, pipeline.no_machine_changes)
    start_time = time()
    new_model.optimize(stopping_callback)
    time_taken = time() - start_time
    return new_model, time_taken


def time_solution_after_warm_start(input_list):
    previous_best_model, _ = time_solution(input_list[:-1])
    _, time_taken = time_solution(
        input_list,
        warm_start_model=previous_best_model)
    return time_taken
