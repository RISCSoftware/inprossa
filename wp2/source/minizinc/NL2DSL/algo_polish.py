import copy
import json
import constants

from BinPackingValidator import validate_solution
from prompt_generation_utils import send_prompt_with_system_prompt, send_polish_feedback, _get_system_prompt, _get_icl, \
    send_prompt_without_system_prompt
from structures_utils import (initial_clean_up, \
                              split_at_outer_equals, Type, load_algopolish_mutation_file,
                              decompose_full_polished_definition,
                              check_functions_appear_twice, State)
from structures_utils_PolishModel import PolishModel, check_executability_for_polish

LOOP_OF_DOOM_UNSAT_MAX_IT = 2
LOOP_OF_DOOM_MAX_IT = 4
MAX_NR_RESETS = 3
N_FAILED_GENERATIONS = 0
FAILED_GENERATIONS = []  # problem desc. indices of failed generation steps

class AlgoPolish:
    POLISHING_ITERATIONS = 2
    POLISHING_MUTATION_TYPES = ["mutation/refactor_experiment.txt", "mutation/refactor_redundancies.txt"]

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
            model_to_be_polished.fitness = 0.3 #model_to_be_polished.calculate_and_set_fitness()
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

            # Mutation - redefine objective function
            mutated_models = []
            for unmutated_model in improved_models:
                mutated_model = copy.deepcopy(unmutated_model)
                mutated_model.set_type(Type.MUTATED)
                old_encoding = mutated_model.get_variables_codeblock() + "\n\n" + mutated_model.objective  + "\n\n" + mutated_model.constraints
                objective_approaches = send_prompt_without_system_prompt(
                    load_algopolish_mutation_file("mutation/ask_for_objective_fun_algorithms.txt").format(
                        problem_description.strip()),
                    self.llm,
                    0.4)
                new_encoding = send_prompt_with_system_prompt(
                    load_algopolish_mutation_file("mutation/refactor_redo_objective_fun.txt").format(old_encoding,
                                                                                                       objective_approaches,
                                                                                                       problem_description.strip()),
                    self.llm,
                    0.95)
                new_model = self._execute_and_validate_model(mutated_model, new_encoding, old_encoding,
                                                             problem_description, m_index)
                if new_model is None: continue

                # Check fitness
                #mutated_model.calculate_and_set_fitness()
                if mutated_model.state == State.CORRECT: mutated_models.append(mutated_model)

#             # Mutation (redundancy-removement, experiment)
#             for unmutated_model in improved_models:
#                 mutated_model = copy.deepcopy(unmutated_model)
#                 mutated_model.set_type(Type.MUTATED)
#
#                 new_encoding = send_prompt_with_system_prompt(
#                                 load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding, problem_description.strip())
#                                 if m_index == 0
#                                 else load_algopolish_mutation_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index]).format(old_encoding),
#                                 self.llm,
#                                 0.85)
#                 new_model = self._execute_and_validate_model(mutated_model, new_encoding, old_encoding, problem_description, m_index)
#                 if new_model is None: continue

#                 # Update model with new encoding
#                 encoding_components = decompose_full_polished_definition(new_encoding)
#                 mutated_model.objective = encoding_components["objective"]
#                 mutated_model.constraints = encoding_components["constraints"]
#
#                 # Check fitness
#                 mutated_model.calculate_and_set_fitness()
#                 if mutated_model.fitness < unmutated_model.fitness:
#                     mutated_models.append(mutated_model)
#                     send_polish_feedback(old_encoding=old_encoding, refactored_encoding=mutated_model.full_formulation, llm=self.llm)
#                 else:
#                     mutated_models.append(unmutated_model)

    def _execute_and_validate_model(self, model: PolishModel, new_encoding: str, old_encoding: str, problem_description: str, m_index: int):
        # Check executability for
        new_encoding = self.enter_feedback_loop(model, new_encoding,
                                            old_encoding, problem_description, m_index)
        if new_encoding is None or model.state == State.FAILED:
            print("Refactoring failed, even with feedback loop.")
            return None
        encoding_components = decompose_full_polished_definition(new_encoding)
        if "objective" in encoding_components:
            model.objective = "#--- Objective ---\n" + encoding_components["objective"]
        if "constraints" in encoding_components:
            model.constraints = "#--- Constraints ---\n" + encoding_components["constraints"]
        validation_result = self._validate_model(model, model.solution_model)
        print(f"""Successful refactoring:
        *******************************************
        Objective value: {model.objective_val}
        Solver time: {model.solve_time}
        Semantic validation: {validation_result}
        *******************************************""")
        return model if model.validated else None

    def enter_feedback_loop(self, model: PolishModel, new_encoding: str, old_encoding: str, problem_description: str, m_index: int):
        execution_error = None
        for _ in range(MAX_NR_RESETS):
            nr_unsat_error = 0
            for i in range(LOOP_OF_DOOM_MAX_IT):
                encoding_components = decompose_full_polished_definition(new_encoding)
                if "objective" in encoding_components:
                    model.objective = encoding_components["objective"]
                if "constraints" in encoding_components:
                    model.constraints = encoding_components["constraints"]
                new_encoding = model.get_variables_codeblock() + \
                                "\n\n#--- Objective ---\n" + model.objective + \
                                "\n\n#--- Constraints ---\n" + model.constraints

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
                    continue

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
                            max_tokens=3000
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
                            max_tokens=3000
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
                            max_tokens=3000
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
                            max_tokens=3000
                        ))
                    execution_error = None
                else:
                    # Safety check: timeout reached and no objective value found
                    if model.solve_time is None:
                        model.state = State.FAILED
                        if constants.DEBUG_MODE_ON: print(
                            f"Timeout reached and no objective value found")
                        new_encoding = (self.llm.send_prompt(
                            system_prompt=( _get_system_prompt("format_sp")) + "\n" + _get_icl(),
                            prompt=f"´´´ python\n" +
                                   f"\n{model.get_variables_codeblock()}\n{new_encoding} ´´´\n\n" +
                                   f"The OptDSL encoding above did not reach a solution within the given timeframe. Improve its efficiency by removing redundancies.",
                            max_tokens=3000))
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
                            max_tokens=3000))
                        continue
                    model.state = State.CORRECT
                    return new_encoding

            # Switch models
            self.llm.send_prompt_with_model_id(
                model_id=(
                    "qwen.qwen3-coder-30b-a3b-v1:0" if self.llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0" else "qwen.qwen3-coder-480b-a35b-v1:0"),
                prompt=""
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

    def _get_elites(self, top_n: int = 10):
        elites = [model for model in self.models if model.objective_val <= self.min_objective_val+4]
        if top_n is not None: elites = self.elites[:top_n]
        return elites


def main():
    # Read problem description
    problem_filepath = "problem_descriptions/2d_bin_packing_inst_1_without_inoutput"
    with open(f"{problem_filepath}.json", "r", encoding="utf-8") as f:
        problem_description_data = json.load(f)
    problem_description = ""
    for description_part in problem_description_data.values():
        if isinstance(description_part, dict): continue
        problem_description += "\n" + description_part if not isinstance(description_part, list) else "\n" + "\n".join(description_part)

    constants.SOLVE_TIME_TIMEOUT = 20000
    polishSomething = AlgoPolish(file_path="models/algopolish_test_smoll.json")
    polishSomething.polish(problem_description)
    constants.SOLVE_TIME_TIMEOUT = 150000

if __name__ == "__main__":
    main()
