from IncrementalPipeline.Objects.board import BoardVars
from IncrementalPipeline.Objects.piece import PieceVars
from IncrementalPipeline.Machines.Pipeline import Pipeline
from gurobipy import Model
from time import time

from IncrementalPipeline.Tools.warm_start import warm_start


class IncrementalMachine():
    def __init__(self, pipeline: Pipeline, input_list):
        self.pipeline = pipeline
        self.input_list = input_list

    def process(self, time_per_step=100):
        """
        When time runs out, modifies the state of the machine
        and sends the current input to the next machine.
        """
        remaining_input = self.input_list[:]
        best_model = Model()
        machine_changes = self.pipeline.no_machine_changes
        print(self.pipeline.intermediate_lists)
        # While there is some input left to process
        while len(remaining_input) > 0 or self.pipeline.empty() is False:
            step_start_time = time()
            # We have time_per_step seconds to decide how to process the current input
            time_left = time_per_step - (time() - step_start_time)
            while time_left > 0 and len(remaining_input) > 0:
                # Continue looking for further solutions
                new_input = remaining_input.pop(0)
                self.pipeline.add_input(new_input)

                best_model, machines_decisions, machines_output = self.optimize_temporal(time_left,
                                       best_model=best_model,
                                       machine_changes=machine_changes)

                time_left = time_per_step - (time() - step_start_time)


                machine_changes = self.pipeline.no_machine_changes
                print(f"Optimization finished with {time_left} seconds left.")
            # TODO take decisions from the same place as the output 
            # extract_decisions(best_model)
            machine_changes = self.pipeline.machine_changes_per_step
            self.pipeline.process_input(best_model, machines_output)
            for machine_id, output_list in machines_output.items():
                print(f"Machine {machine_id} produced output:")
                for output in output_list:
                    if isinstance(output, BoardVars):
                        print(f" - Board {output.id} with length {output.length.X}")
                    elif isinstance(output, PieceVars):
                        print(f" - Piece {output.id} with length {output.length.X} good {output.good.X}")

    def optimize_temporal(self,
                          remaining_time,
                          best_model=Model(),
                          machine_changes=None):
        new_model = Model()

        machines_decisions, machines_output = self.pipeline.impose_conditions(new_model)

        # initialise the values with the solution from previous model
        warm_start(new_model, best_model, machine_changes)
        # optimise with the remaining time

        new_model.setParam('TimeLimit', remaining_time)
        new_model.optimize()

        # TODO in the future compare some metric to decide whether to keep as best model
        # For now, simply keep the last model as the best one
        # if this is ever changed machine_decisions and machines_output should be changed accordingly
        best_model = new_model

        return best_model, machines_decisions, machines_output

    def optimize(self,
                 remaining_time,
                 best_model=Model(),
                 machine_changes=None):
        start_time = time()
        for i in range(len(self.input_list)):
            current_input = self.input_list[:i+1]
            # create new model
            new_model = Model()

            decisions, output = self.pipeline.impose_conditions(
                new_model,
                input_list=current_input)
            
            # initialise the values with the solution from previous model
            warm_start(new_model, best_model, machine_changes)
            # optimise with the remaining time

            time_left = max(0, remaining_time - (time() - start_time))
            new_model.setParam('TimeLimit', time_left)
            new_model.optimize()

            # TODO in the future compare some metric to decide whether to keep as best model
            # For now, simply keep the last model as the best one
            best_model = new_model
            
            # No change has been made to the machines
            machine_changes = {
                machine.id: (0,0)
                for machine in self.pipeline.machines
            }
        return best_model