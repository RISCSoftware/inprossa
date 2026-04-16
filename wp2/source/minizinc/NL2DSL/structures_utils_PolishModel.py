import copy
import random
import json
import os
import re

import constants

from enum import Enum
from datetime import datetime
from model_reuser import ModelReuser
from structures_utils import initial_clean_up, remove_programming_environment, State, is_valid_json, execute_code_block


class Type(Enum):
    UNMODIFIED = "unmodified"
    MUTATED = "muted"
    MERGED = "merged"

class PolishModel:
    FILE_NAME = "data.json"

    @staticmethod
    def calculate_fitness(objective_val: float, solve_time: float) -> float:
        return objective_val + solve_time #+ ((len(objective) + len(constraints)) / 100000)

    def __init__(self, model: dict, id: int = 0, save_model:bool = False):
        self.model = model
        self.problem_description = model["problem_description"]
        self.llm_generated_objects = model["llm_generated_objects"]
        self.script_generated_objects = model["script_generated_objects"]
        self.constants = model["constants"]
        self.decision_variables = model["decision_variables"]
        self.objective = model["objective"]
        self.constraints = model["constraints"]
        self.objective_val = model["objective_val"]
        self.full_formulation = model["full_formulation"]
        self.solution_model = model["solution_model"]
        self.solve_time = model["solve_time"]
        self.fitness = 0
        self.id = f"{id if id is not None else random.randint(0, 100)}"
        self.path = f"/{self.id}"
        self.save_model = save_model
        self.state = State.UNINITIALIZED
        self.validated = False
        self.type = Type.UNMODIFIED

    def set_type(self, type: Type):
        self.type = type
        self.id = f"{type}_{self.id}"

    def get_as_dict(self):
        return {
            "problem_description": copy.deepcopy(self.problem_description),
            "llm_generated_objects": initial_clean_up(self.llm_generated_objects),
            "script_generated_objects": copy.deepcopy(self.script_generated_objects),
            "constants": copy.deepcopy(self.constants),
            "decision_variables": copy.deepcopy(self.decision_variables),
            "objective": initial_clean_up(self.objective),
            "constraints": initial_clean_up(self.constraints),
            "full_formulation": self.full_formulation,
            "objective_val": self.objective_val,
            "solution_model": {},
            "solve_time": self.solve_time,
            "final_evaluation_result": ""
        }

    def calculate_and_set_fitness(self):
        self._test_on_testing_set()
        if self.state == State.FAILED:
            return
        self.fitness = PolishModel.calculate_fitness(self.objective_val, self.solve_time)

    def _test_on_testing_set(self):
        test_instances = os.listdir(constants.ALGOPOLISH_TESTSET_PATH)
        test_instances.sort()
        repeat_testing_set = len(test_instances)//2
        repeat_testing_set = repeat_testing_set if repeat_testing_set > 0 else 1

        testset_objective_vals = [[] for _ in range(repeat_testing_set)]
        testset_solve_times = [[] for _ in range(repeat_testing_set)]
        test_object = self.get_as_dict()
        for i in range(repeat_testing_set):
            for test_instance in test_instances:
                try:
                    model = ModelReuser.use_given_model_with_input(test_object,
                        os.path.join(constants.ALGOPOLISH_TESTSET_PATH,
                        test_instance))
                except Exception as e:
                    print(e)
                    self.objective_val = 20
                    self.solve_time = 10000
                    self.state = State.FAILED
                    return

                if model["state"] == State.FAILED or not model["objective_val"]:
                    self.objective_val = 20
                    self.solve_time = 10000
                    self.state = State.FAILED
                    return
                testset_objective_vals[i].append(model["objective_val"])
                testset_solve_times[i].append(model["solve_time"])
        #print(f"Testset (20 inst.) 10 runs - objectives: {testset_objective_vals}")
        #print(f"Testset (20 inst.) 10 runs - solvetimes: {testset_solve_times}")
        self.objective_val = sum([(sum(run_sum) / len(run_sum)) for run_sum in testset_objective_vals]) / len(
            testset_objective_vals)
        self.solve_time = sum([(sum(run_sum) / len(run_sum)) for run_sum in testset_solve_times]) / len(
            testset_solve_times)

    def save_model_to_file(self, final_evaluation_result, filename: str = f'mutated_optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        data = {
            "problem_description": self.problem_description,
            "llm_generated_objects": self.llm_generated_objects,
            "script_generated_objects": self.script_generated_objects,
            "constants": self.constants,
            "decision_variables": self.decision_variables,
            "objective": self.objective,
            "constraints": self.constraints,
            "full_formulation": self.full_formulation,
            "state": self.state,
            "objective_val": self.objective_val,
            "solution_model": self.solution_model,
            "solve_time": self.solve_time,
            "final_evaluation_result": final_evaluation_result
        }
        # Append new model to existing collection
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        existing_data.append(data)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)

    def get_variables_codeblock(self):
        block = "# --- Objects ---\n"
        block += f"{self.llm_generated_objects}\n"
        for object_name, object_spec in self.script_generated_objects.items():
            block += object_spec + "\n"
        block += "\n# --- Constants and Decision Variables ---\n"
        for constant in self.constants:
            block += constant["initialization"] + "\n"
        for constant in self.decision_variables:
            block += constant["initialization"] + "\n"
        return block

    def set_content(self, content, failed: bool = False):
        self.full_formulation = ""
        content = remove_programming_environment(content.strip())
        self.full_formulation += content

        if content.strip() == "" or failed:
            self.state = State.FAILED
            self.full_formulation += 1
        else:
            if self.state == State.UNINITIALIZED: self.state = State.CORRECT

def check_executability_for_polish(raw_code : str, model: PolishModel):
    m = re.search(r'Annotated\[\s*list\[\s*(?P<elem_type>int|float|bool)\s*]\s*,\s*Len\(\s*\d+\s*,\s*(?P<max>\d+)\s*\)\s*]',
              raw_code)
    if "Annotated[list[" in raw_code and m:
        return f"Error: for this list elem_type must have a type of typing.Annotated with a pydantic.Field of type int, float, bool: {m.group(0)}\nE.g.: Annotated[list[int], Len(5, 5)]"

    # Safety check: no json has be returned instead of code
    if is_valid_json(raw_code) or raw_code.startswith("{") or raw_code.startswith("["):
        return f"Error: Result must not be json objects, valid {constants.CHOSEN_LANGUAGE} code."

    # Result must not be empty
    if raw_code == "": return "Error - Invalid result: Result is empty."

    # Safety check: check that there are no non-constants in range
    m = re.search(r"range\((?:\s*(?=[^,\(\)\[\]]+[a-z])[^,\(\)\[\]]+,\s*[^)]+|\s*[^,\(\)\[\]]+,\s*(?=[^) ]+[a-z])[^)]+)\):", raw_code)
    if m:
        return f"Error - range incorrectly used. Correct use is range(<val_1>,<val_2>) where val_1 and val_2 must be a constant variable or a integer value: {m.group(0)}"

    # Execute code block of partial/full formulation
    return execute_code_block(raw_code, model, include_solver_execution=True)
