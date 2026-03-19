import copy
import json
import re

import constants
from BinPackingValidator import validate_solution
from input_reader import InputReader
from model_reuser import ModelReuser
from prompt_generation_utils import send_prompt_with_system_prompt, send_polish_feedback, _get_system_prompt, _get_icl, \
    send_prompt_without_system_prompt
from structures_utils import (initial_clean_up, PolishModel, check_executability_for_polish, \
    split_at_outer_equals, Type, load_algopolish_mutation_file, decompose_full_polished_definition,
                              check_functions_appear_twice)

LOOP_OF_DOOM_UNSAT_MAX_IT = 2
LOOP_OF_DOOM_MAX_IT = 4
MAX_NR_RESETS = 3
N_FAILED_GENERATIONS = 0
FAILED_GENERATIONS = []  # problem desc. indices of failed generation steps

class AlgoPolish:
    POLISHING_ITERATIONS = 2
    POLISHING_MUTATION_TYPES = ["mutation/refactor_redo_objective_fun.txt", "mutation/refactor_experiment.txt", "mutation/refactor_redo_objective_fun.txt", "mutation/refactor_redundancies.txt"]

    def __init__(self, file_path: str = None, models: list[dict] = None):
        if file_path is not None:
            with open(file_path, "r", encoding="utf-8") as f:
                models = json.load(f)
        self.models: list[PolishModel] = []
        self.elites: list[PolishModel] = []
        self.llm = constants.get_LLM_client()
        assert models is not None, "Either file_path or models must be given."
        # Convert from OptDSL to pydantic for Mutation by LLM
        for i, model in enumerate(models):
            model_to_be_polished = PolishModel(model)
            model_to_be_polished.objective = initial_clean_up(model_to_be_polished.objective, to_typing=True)
            model_to_be_polished.constraints = initial_clean_up(model_to_be_polished.constraints, to_typing=True)
            model_to_be_polished.calculate_and_set_fitness()
            self.models.append(model_to_be_polished)
        fitness_vals = [model.fitness for model in self.models]
        self.cur_avg_fitness = sum(fitness_vals) / len(fitness_vals)
        self.min_objective_val = min([model.objective_val for model in self.models])
        self.elites = self._get_elites()


    def polish (self, problem_description: str):
        improved_models = self.models

        for m_index in range(AlgoPolish.POLISHING_ITERATIONS):
            # Biased Crossover
            merged_models = []
            # for elite in self.elites:
            #     for model in [x for x in self.models if x not in self.elites]:
            #         if model != elite:
            #             elite_encoding = elite.objective + "\n\n" + elite.constraints
            #             non_elite_encoding = model.objective + "\n\n" + model.constraints
            #             encoding = send_prompt_with_system_prompt(
            #                 load_algopolish_mutation_file("crossover/crossover_biased_80%.txt").format(elite_encoding,
            #                                                                                            non_elite_encoding,
            #                                                                                            80,
            #                                                                                            20),
            #                 self.llm)
            #             new_model = self._execute_and_validate_model(encoding, copy.deepcopy(elite))
            #             if new_model is None: continue
            #             merged_models.append(new_model)

            # Mutation
            mutated_models = []
            for unmutated_model in improved_models:
                mutated_model = copy.deepcopy(unmutated_model)
                mutated_model.set_type(Type.MUTATED)
                m_index = 0

                if m_index == 0:
                    old_encoding = mutated_model.get_variables_codeblock() + "\n\n" + mutated_model.objective #+ "\n\n" + mutated_model.constraints
                    objective_approaches = send_prompt_without_system_prompt(
                        load_algopolish_mutation_file("mutation/ask_for_objective_fun_algorithms.txt").format(problem_description.strip()),
                        self.llm,
                        0.4)
                    new_encoding = send_prompt_with_system_prompt(
                                    load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding, objective_approaches, problem_description.strip())
                                    if m_index == 0
                                    else load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding),
                                    self.llm,
                                    0.85)
                    new_model = self._execute_and_validate_model(mutated_model, new_encoding, old_encoding, problem_description, m_index)
                if new_model is None: continue
                print(f"""Successful refactoring:
*******************************************
Obj. + Constraints: {new_encoding}
Objective value: {mutated_model.objective_val}
Solver time: {mutated_model.solve_time}
Semantic validation: {new_model.solution_model}
*******************************************""")
                # Update model with new encoding
                encoding_components = decompose_full_polished_definition(new_encoding)
                mutated_model.objective = encoding_components["objective"]
                mutated_model.constraints = encoding_components["constraints"]

                # Check fitness
                mutated_model.calculate_and_set_fitness()
                if mutated_model.fitness < unmutated_model.fitness:
                    mutated_models.append(mutated_model)
                    send_polish_feedback(old_encoding=old_encoding, refactored_encoding=mutated_model.full_formulation, llm=self.llm)
                else:
                    mutated_models.append(unmutated_model)

    def _execute_and_validate_model(self, model: PolishModel, new_encoding: str, old_encoding: str, problem_description: str, m_index: int):
        encoding_components = decompose_full_polished_definition(new_encoding)
        # # Check executability for objective function
        model.objective = encoding_components["objective"]
        # response = self.enter_feedback_loop(model, model.get_variables_codeblock() + "#--- Objective ---\n" + model.objective,
        #                                     old_encoding, problem_description, m_index)
        # if response is None:
        #     print("Refactoring failed, even with feedback loop.")
        #     return None
        # Check executability for constraints
        model.constraints = encoding_components["constraints"]
        new_encoding = self.enter_feedback_loop(model,
                                            model.get_variables_codeblock() +
                                            "\n#--- Objective ---\n" + model.objective +
                                            "\n#--- Constraints ---\n" + model.constraints,
                                            old_encoding, problem_description, m_index)
        if new_encoding is None:
            print("Refactoring failed, even with feedback loop.")
            return None
        encoding_components = decompose_full_polished_definition(new_encoding)
        model.objective = encoding_components["objective"]
        model.constraints = encoding_components["constraints"]
        # execution_error = check_executability_for_polish(model.get_variables_codeblock()
        #                                                  + "\n\n"
        #                                                  + encoding, model)
        # if execution_error is not None:
        #     print(f"Execution error: {execution_error}")
        #     return None
        validation_result = self._validate_model(model, model.solution_model)
        print(f"""Successful refactoring:
        *******************************************
        Obj. + Constraints: {new_encoding}
        Objective value: {model.objective_val}
        Solver time: {model.solve_time}
        Semantic validation: {validation_result}
        *******************************************""")
        return model

    def enter_feedback_loop(self, model: PolishModel, new_encoding: str, old_encoding: str, problem_description: str, m_index: int):
        execution_error = None
        for _ in range(MAX_NR_RESETS):
            nr_unsat_error = 0
            for i in range(LOOP_OF_DOOM_MAX_IT):
                # Send prompt anew, no feedback loop
                if ("NTD" in new_encoding or
                    "Minizinc Solver Error" in new_encoding or
                    (execution_error is not None and "Constraints FormatError" in execution_error) or
                    (execution_error is not None and "Constraints/Objective FormatError" in execution_error) or
                    new_encoding.strip() == "" or
                    nr_unsat_error == LOOP_OF_DOOM_UNSAT_MAX_IT):
                    if constants.DEBUG_MODE_ON: print(
                        f"Checking model: {new_encoding}\nNTD, solver error, format error or end of loop of doom encountered")
                    new_encoding = send_prompt_with_system_prompt(
                        load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding, problem_description.strip())
                        if m_index == 0
                        else load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding),
                        self.llm,
                        0.9)
                    execution_error = None
                    nr_unsat_error = 0

                # Check for syntactical correctness and handle execution error, if no "Constraints/Objective FormatError" has occurred yet
                if execution_error is None:
                    execution_error = check_executability_for_polish(new_encoding, model)
                # Handle execution error
                if execution_error is not None:
                    if "type error" in execution_error and "\\/" in execution_error:
                        execution_error = "Incompatible types used in one of the or-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the or-expressions, only boolean can be used with or-expressions."
                    elif "type error" in execution_error and "/\\" in execution_error:
                        execution_error = "Incompatible types used in one of the and-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the and-expressions, only boolean can be used with and-expressions."

                    if constants.DEBUG_MODE_ON: print(
                        f"Checking node created for model: {execution_error}\n")
                    if ("NTD" in new_encoding or
                        (execution_error is not None and "Constraints FormatError" in execution_error) or
                        (execution_error is not None and "Constraints/Objective FormatError" in execution_error)):
                        if constants.DEBUG_MODE_ON: print(
                            f"Checking node created for model: {new_encoding}\nNTD, Constraints FormatError or Constraints/Objective ForamtErrorencountered")
                        new_encoding = send_prompt_with_system_prompt(
                            load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(
                                old_encoding, problem_description.strip())
                            if m_index == 0
                            else load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(
                                old_encoding),
                            self.llm)
                        execution_error = None
                        continue
                    elif "Syntax Error" in execution_error:
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=_get_system_prompt("format_sp") + "\n" + _get_icl(),
                            prompt=f"´´´python\n" +
                                   f"\n# --- Incorrect Code --- \n{new_encoding}´´´\n\n" +
                                   f"The section above contains a syntax error: {execution_error}" +
                                   "Given this error message, improve the mentioned lines of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return \nNTD\n."
                                   """Return your answer in the format
    ´´´python
    # --- Incorrect Code ---
    <corrected code>
    ´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                                   """,
                            max_tokens=1000
                        ))
                    elif "Semantic Error" in execution_error:
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=_get_system_prompt(
                                "format_sp") + "\n" + _get_icl(),
                            prompt=f"´´´python\n" +
                                   f"\n# --- Incorrect Code --- \n{new_encoding}´´´\n\n" +
                                   f"The section above contains a semantic error: {execution_error}" +
                                   "Given this error message, improve the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else." +
                                   f"The semantics of the section \"# --- Incorrect Code ---\" must be in line with the following description:\n{problem_description}" +
                                   """
    Define more bounds for variables. Reduce the number of temporary variables.
    Return your answer in the format
    ´´´python
    # --- Incorrect Code ---
    <corrected code>
    ´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                                   """,
                            max_tokens=1000
                        ))
                        nr_unsat_error += 1
                    elif "Memory violation" in execution_error:
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=_get_system_prompt("format_sp") + _get_icl(),
                            prompt=f"´´´python\n" +
                                   f"\n# --- Incorrect Code --- \n{new_encoding}´´´\n\n" +
                                   f"Improve the code of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet as follows: Inline expressions and list accesses instead of creating temporary variables. Reduce the number of temporary variables. Increase efficiency of constraints and reduce constraint length." +
                                   "Nothing else. Do not change the semantics of the code. Do not return NTD."
                                   "Return your answer in the format\n" +
                                   "´´´python\n" +
                                   "# --- Incorrect Code ---\n" +
                                   "<corrected code>\n" +
                                   "\n´´´, where <corrected code> all lines underneath \"# --- Incorrect Code ---\" with the corrections.",
                            max_tokens=1500
                        ))
                    else:
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=_get_system_prompt("format_sp") + _get_icl(),
                            prompt=f"´´´python\n" +
                                   f"\n# --- Incorrect Code --- \n{new_encoding}´´´\n\n" +
                                   f"The code snipped above contains the following error: \"{execution_error}\"" +
                                   "Improve the mentioned lines of the section \"# --- Incorrect Code ---\" - code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return NTD."
                                   "Return your answer in the format\n" +
                                   "´´´python\n" +
                                   "# --- Incorrect Code ---\n" +
                                   "<corrected code>\n" +
                                   "\n´´´, where <corrected code> are all lines underneath \"# --- Incorrect Code ---\" including the corrections.",
                            max_tokens=1500
                        ))
                    execution_error = None
                else:
                    # Safety check: Prevent false-positive exec-run-through by sneakily never calling function
                    not_twice_appearing_func = check_functions_appear_twice(new_encoding)
                    if len(not_twice_appearing_func) > 0:
                        if constants.DEBUG_MODE_ON: print(
                            f"The following functions are defined but never called, {not_twice_appearing_func}. Add the missing function calls.")
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=(
                                              _get_system_prompt(
                                                  "json_sp") if model.level == 2 else _get_system_prompt(
                                                  "format_sp")) + "\n" + _get_icl(),
                            prompt=f"´´´ python\n" +
                                   f"\n{model.get_partial_formulation_up_until_now()}\n{new_encoding} ´´´\n\n" +
                                   f"The following functions are defined but never called, {not_twice_appearing_func}" +
                                   "Add the missing function calls to the code with the correct parameters. Do not return exactly the given code snippet.",
                            max_tokens=800))
                        continue
                    return new_encoding

            # Attempt reset
            self.llm.send_prompt_with_model_id(
                model_id=(
                    "qwen.qwen3-coder-30b-a3b-v1:0" if self.llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0" else "qwen.qwen3-coder-480b-a35b-v1:0"),
                prompt="",
                max_tokens=1
            )
            new_encoding = model.get_variables_codeblock() + send_prompt_with_system_prompt(
                load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(
                    old_encoding, problem_description.strip())
                if m_index == 0
                else load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(
                    old_encoding),
                self.llm)
        return ""

    def _validate_model(self, model: PolishModel, solution_model):
        # Validate minizinc solution
        task = {}
        if model.constants:
            vars = {}
            for variable in model.constants:
                vars.update({variable["variable_name"]:
                                 split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[
                                     0].strip()})
            task.update({"input": vars})
        try:
            validate_solution(solution_model, task)
        except AssertionError as e:
            validation_res = f"Failed to validate solution: {e}"
            model.validated = False
        except Exception as e:
            validation_res = f"Evaluation failed: {e}"
            model.validated = False
        else:
            validation_res = f"Successfully validated solution."
            model.validated = True
        return validation_res

    def _get_elites(self, top_n: int = None):
        #elites = [model for model in self.models if model.fitness > self.cur_avg_fitness]
        elites = [model for model in self.models if model.objective_val <= self.min_objective_val+4]
        if top_n is not None: elites = self.elites[:top_n]
        return elites

    def _test_on_training_set(self):
        model = self.models[0]
        model = ModelReuser.use_given_model_with_input(model.get_as_dict(), "problem_descriptions/testset/test_inst_3.json")
        i = 5
        return model["objective_val"]

def main():
    # Read problem description
    problem_filepath = "problem_descriptions/2d_bin_packing_inst_1_without_inoutput"
    with open(f"{problem_filepath}.json", "r", encoding="utf-8") as f:
        problem_description_data = json.load(f)
    problem_description = ""
    for description_part in problem_description_data.values():
        if isinstance(description_part, dict): continue
        problem_description += "\n" + description_part if not isinstance(description_part, list) else "\n" + "\n".join(description_part)

    polishSomething = AlgoPolish(file_path="models/optDSL_models_2026-03-09_15-42.json")
    polishSomething.polish(problem_description)
    #polishSomething._test_on_training_set()


if __name__ == "__main__":
    main()
