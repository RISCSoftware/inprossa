from IncrementalPipeline.Objects.board import BoardVars
from IncrementalPipeline.Machines.Pipeline import Pipeline
from gurobipy import Model
from time import time

from IncrementalPipeline.Tools.warm_start import warm_start


class IncrementalMachine():
    def __init__(self, pipeline: Pipeline, input_list):
        self.pipeline = pipeline
        self.input_list = input_list

    def process(self, machine_changes_per_step, time_per_step=10):
        """
        When time runs out, modifies the state of the machine
        and sends the current input to the next machine.
        """
        remaining_input = self.input_list[:]
        best_model = Model()
        # While there is some input left to process
        while len(remaining_input) > 0 and self.pipeline.empty() is False:
            step_start_time = time()
            # We have time_per_step seconds to decide how to process the current input
            time_left = time_per_step - (time() - step_start_time)
            while time_left > 0:
                # Continue looking for further solutions
                new_input = remaining_input.pop(0)
                self.pipeline.add_input(new_input)
                self.optimize(time_left,
                              previous_model=best_model,
                              machine_changes_per_step=machine_changes_per_step)
                # Remove the processed input from the remaining input
                remaining_input.pop(0)
            self.pipeline.process_input(remaining_input, machine_changes_per_step)
            

    def optimize(self,
                 remaining_time,
                 previous_model=Model(),
                 machine_changes=None):
        start_time = time()
        for i in range(len(self.input_list)):
            current_input = self.input_list[:i+1]
            # create new model
            new_model = Model()

            # TODO the following two lines would be better inside the pipeline
            # OR a function to_BoardsVars can be created in Board
            starting_machine_name = self.pipeline.machines[0].id
            vars_current_input = [
                BoardVars(new_model, board=board, id=f"{starting_machine_name} board [{i}]")
                for i, board in enumerate(current_input)
            ]
            self.pipeline.impose_conditions(new_model,
                                            input_list=vars_current_input)
            
            # initialise the values with the solution from previous model
            warm_start(new_model, previous_model, machine_changes)
            # optimise with the remaining time

            time_left = max(0, remaining_time - (time() - start_time))
            new_model.setParam('TimeLimit', time_left)
            new_model.optimize()

            
            
            # No change has been made to the machines
            machine_changes = {
                machine.id: (0,0)
                for machine in self.pipeline.machines
            }

