from IncrementalPipeline.Objects.board import BoardVars
from IncrementalPipeline.Machines.Pipeline import Pipeline
from gurobipy import Model
from time import time

from IncrementalPipeline.Tools.warm_start import warm_start


class IncrementalMachine():
    def __init__(self, pipeline: Pipeline, input_list):
        self.pipeline = pipeline
        self.input_list = input_list

    def optimize(self, remaining_time, previous_model=Model()):
        start_time = time()
        for i in range(len(self.input_list)):
            current_input = self.input_list[:i+1]
            # create new model
            new_model = Model()
            vars_current_input = [BoardVars(new_model, board=board, id=f"board-{i}") for i, board in enumerate(current_input)]
            self.pipeline.impose_conditions(new_model,
                                            input_list=vars_current_input)
            # initialise the values with the solution from previous model
            warm_start(new_model, previous_model)
            # optimise with the remaining time

            time_left = max(0, remaining_time - (time() - start_time))
            new_model.setParam('TimeLimit', time_left)
            new_model.optimize()

