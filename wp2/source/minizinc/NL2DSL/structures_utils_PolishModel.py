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
        """
        Calculates the AlgoPolish heuristic to determine how fit a formulation is. A low value is desirable.
        Args:
            objective_val (float): The objective value of the formulation.
            solve_time (float): The solve time of the formulation.
        """
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
        """
        Calculates algopolish heuristic with a test set and sets it as property.
        """
        self._test_on_testing_set()
        if self.state == State.FAILED:
            return
        self.fitness = PolishModel.calculate_fitness(self.objective_val, self.solve_time)

    def _test_on_testing_set(self):
        """
        To determine fitness of a formulation, test it on a separate test set and
        repeat 10x to consider the solver's variability in solvetime.
        """
        test_instances = os.listdir(constants.ALGOPOLISH_TESTSET_PATH)
        test_instances.sort()
        repeat_testing_set = 10
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
                    print("Exception during testing: " + str(e))
                    self.objective_val = 20
                    self.solve_time = constants.SOLVE_TIME_TIMEOUT
                    self.state = State.FAILED
                    return

                if (model["state"] == State.FAILED.value or
                    model["objective_val"] is None or
                    model["solve_time"] is None or
                    (constants.ALGOPOLISH_ACTIVE and
                     sum(solve_time > (constants.SOLVE_TIME_TIMEOUT/1000 - 1) for solve_time in testset_solve_times[i]) > 5)):
                        self.objective_val = 20
                        self.solve_time = constants.SOLVE_TIME_TIMEOUT
                        self.state = State.FAILED
                        return
                testset_objective_vals[i].append(model["objective_val"])
                testset_solve_times[i].append(model["solve_time"])
        self.objective_val = sum([(sum(run_sum) / len(run_sum)) for run_sum in testset_objective_vals]) / len(
            testset_objective_vals)
        self.solve_time = sum([(sum(run_sum) / len(run_sum)) for run_sum in testset_solve_times]) / len(
            testset_solve_times)

    def save_model_to_file(self, final_evaluation_result, filename: str = f'mutated_optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        """
        Write formulation incl. meta data like objective value, successful semantic evaluation to file.
        Args:
            final_evaluation_result (): Result from semantic evaluation (with user-given validator).
            filename (str): The name of the file to save to.
        """
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
        """
        Return formulation code block containing Object types and Constants with Decision Variables
        """
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


def load_algopolish_mutation_file(file_path) -> str:
    """
    Load prompt template for AlgoPolish (for merge- or refactoring prompt).
    Args:
        file_path (str): Path to the file (prompt template) to load.
    """
    file_path = "prompts/algopolish/" + file_path
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def decompose_full_polished_definition(full_definition: str):
    """
    Decompose full raw formulation from LLM into different components according to format convention
    for OptDSL formulations taken for this framework.
    Args:
        full_definition (str): Full raw formulation from LLM.
    """
    if ("# --- Objects ---".lower() in full_definition.lower() or
        "# --- Constants ---".lower() in full_definition.lower() or
        "# --- Decision variables ---".lower() in full_definition.lower() or
        "# --- Constants and Decision Variables ---".lower() in full_definition.lower() or
        "# --- Objective ---".lower() in full_definition.lower() or
        "# --- Auxiliary Variables ---".lower() in full_definition.lower() or
        "# --- Constraints ---".lower() in full_definition.lower() or
        "# --- Incorrect Code ---".lower() in full_definition.lower()):
        full_definition = remove_programming_environment(full_definition)
        blocks = {}
        current_key = None
        temp = []

        for line in full_definition.splitlines():
            # Detect a block header, e.g. "--- Objects ---"
            m = re.match(r'(?:^\s*)#\s*--+\s*(\w+(?:\s+\w+)*)\s*--+', line)
            if m:
                if not ((m.group(1).strip().lower() == "constraints" or m.group(
                    1).strip().lower() == "auxiliary variables")
                        and (current_key == "constraints" or current_key == "auxiliary variables")):
                    current_key = m.group(1).strip().lower()
                    blocks[current_key] = []
            else:
                if current_key is not None:
                    if len(temp) > 0:
                        blocks[current_key] = temp + blocks[current_key]
                        temp = []
                    blocks[current_key].append(line)
                else:
                    if len(line) > 0: temp.append(line)

        # Convert lists into single strings
        for k in blocks:
            blocks[k] = "\n".join(blocks[k]).strip()
        return blocks
    return None

def check_executability_for_polish(raw_code : str, model: PolishModel):
    """
        Check executability with OptDSL-translator and MiniZinc solver.
        Note: In contrast, to check_executability from ToT generation, we do not need to consider formulation components of
        different tree levels, simply the full formulation needs to be checked. Consequently, this method is the lean version of the ToT-version.
        Args:
             raw_code (str): Raw full OptDSL-formulation.
             model (PolishModel): model to eventually hold the formulation from raw_code (incl. solve metadata),
             if raw_code is syntactically ok and its solution is valid.
    """

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
