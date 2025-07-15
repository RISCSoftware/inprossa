"""
Define an industrial pipeline for wood processing

The object will initially take a list of the machines that create the pipeline.
"""

from IncrementalPipeline.Machines.GenericMachine import GenericMachine
from typing import List


class Pipeline(GenericMachine):
    """
    Defines a pipeline of machines.

    The object will initially take a list
    of the machines that create the pipeline.

    List of objects inbetween each two machines will be defined
    """

    def __init__(self,
                 id: str,
                 machines: List[GenericMachine],
                 intermediate_lists: List[List] = None):
        self.machines = machines
        if intermediate_lists is None:
            self.intermediate_lists = [list()
                                       for _ in range(len(machines) + 1)]
        else:
            self.intermediate_lists = intermediate_lists

        # Check correctness of the pipeline
        self.correctness()
        super().__init__(id=f"Pipeline-{id}",
                         input_type=machines[0].input_type,
                         output_type=machines[-1].output_type)
        self.decisions = dict()

        # One by one process the machines, adding their output
        # to the already existing intermediate lists

    def impose_conditions(self, model, input_list: list) -> None:
        """
        Imposes conditions on the model based on the input list.
        Each machine in the pipeline will impose its own conditions.
        """
        list_to_process = self.intermediate_lists[0] + input_list
        print(list_to_process)
        for index, machine in enumerate(self.machines):
            decisions_list, output_list = machine.impose_conditions(model, list_to_process)
            self.decisions[machine.id] = decisions_list
            list_to_process = self.intermediate_lists[index + 1] + output_list

        return list_to_process

    def correctness(self):
        """
        Checks the correctness of the pipeline.
        Ensures that the output of each former machine
        is the input of the latter.
        """
        for i in range(len(self.machines) - 1):
            if self.machines[i].output_type != self.machines[i + 1].input_type:
                raise ValueError(
                    f"Machine {self.machines[i].id} output type "
                    f"{self.machines[i].output_type} does not match "
                    f"next machine {self.machines[i + 1].id} input type "
                    f"{self.machines[i + 1].input_type}."
                )

    def create_pipeline(self):
        """
        Creates the pipeline by binding the machines together.
        """
        current_type = list  # Starting with a list type
        for machine in self.machines:
            current_type = machine.bind(current_type)
        return current_type

    def add_input(self, input):
        """
        Adds input to the first element of intermediate_lists.
        """
        self.intermediate_lists[0].append(input)

    def process_input(self, decisions, machine_changes_per_step):
        """
        Actualises the intermediate lists based on the decisions and machine changes.
        """
        for i, machine in enumerate(self.machines):
            decisions_list = decisions[machine.id]
            changes_per_step = machine_changes_per_step[machine.id]
            remaining_input, output = machine.process(decisions_list,
                                                      changes_per_step,
                                                      self.intermediate_lists[i])
            # Add the output to the next intermediate list
            self.intermediate_lists[i + 1].extend(output)
            self.intermediate_lists[i] = remaining_input

    def empty(self):
        """
        Returns true if all intermediate lists are empty.
        """
        return all(len(lst) == 0 for lst in self.intermediate_lists)