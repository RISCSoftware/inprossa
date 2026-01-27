import copy
import json

import constants
from BinPackingValidator import validate_solution
from prompt_generation_utils import send_prompt_with_system_prompt
from structures_utils import initial_clean_up, PolishModel, check_executability_for_polish, \
    _split_at_outer_equals, Type, load_algopolish_file, decompose_full_polished_definition


class AlgoPolish:
    POLISHING_ITERATIONS = 2
    POLISHING_MUTATION_TYPES = ["mutation/refactor_solvingtime.txt", "mutation/refactor_redundancies.txt"]

    def __init__(self, file_path: str = None, models: list[dict] = None):
        if file_path is not None:
            with open(file_path, "r", encoding="utf-8") as f:
                models = json.load(f)
        self.models: list[PolishModel] = []
        self.elites: list[PolishModel] = []
        self.llm = constants.LLM
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


    def mutate (self):
        improved_models = self.models

        for m_index in range(AlgoPolish.POLISHING_ITERATIONS):
            # Biased Crossover
            merged_models = []
            for elite in self.elites:
                for model in improved_models:
                    if model != elite:
                        elite_encoding = elite.objective + "\n\n" + elite.constraints
                        non_elite_encoding = model.objective + "\n\n" + model.constraints
                        encoding = send_prompt_with_system_prompt(
                            load_algopolish_file("crossover/crossover_biased_80%.txt").format(elite_encoding,
                                                                                              non_elite_encoding,
                                                                                              80,
                                                                                              20),
                            self.llm)
                        new_model = self._execute_and_validate_model(encoding, copy.deepcopy(elite))
                        if new_model is None: continue
                        merged_models.append(new_model)

            # Mutation
            mutated_models = []
            for unmutated_model in improved_models:
                mutated_model = copy.deepcopy(unmutated_model)
                mutated_model.set_type(Type.MUTETED)
                encoding = mutated_model.objective + "\n\n" + mutated_model.constraints
                encoding = send_prompt_with_system_prompt(
f"""[Code]
```python
{encoding}
```

{load_algopolish_file(AlgoPolish.POLISHING_MUTATION_TYPES[m_index])}""",
                self.llm)
                execution_error = check_executability_for_polish(mutated_model.llm_generated_objects
                                                                 + "\n\n"
                                                                 + mutated_model.get_variables_codeblock()
                                                                 + "\n\n"
                                                                 + encoding, mutated_model)
                if execution_error is not None:
                    print(f"Execution error: {execution_error}")
                    continue
                validation_result = self._validate_model(mutated_model, mutated_model.solution_model)
                print(f"""Successful refactoring:
*******************************************
Obj. + Constraints: {encoding}
Objective value: {mutated_model.objective_val}
Solver time: {mutated_model.solve_time}
Semantic validation: {validation_result}
*******************************************""")
                encoding_components = decompose_full_polished_definition(encoding)
                mutated_model.objective = encoding_components["objective"]
                mutated_model.constraints = encoding_components["constraints"]
                mutated_model.calculate_and_set_fitness()
                if mutated_model.fitness < unmutated_model.fitness:
                    mutated_models.append(mutated_model)
                else:
                    mutated_models.append(unmutated_model)

    def _execute_and_validate_model(self, encoding: str, model: PolishModel):
        execution_error = check_executability_for_polish(model.llm_generated_objects
                                                         + "\n\n"
                                                         + model.get_variables_codeblock()
                                                         + "\n\n"
                                                         + encoding, model)
        if execution_error is not None:
            print(f"Execution error: {execution_error}")
            return None
        validation_result = self._validate_model(model, model.solution_model)
        print(f"""Successful refactoring:
        *******************************************
        Obj. + Constraints: {encoding}
        Objective value: {model.objective_val}
        Solver time: {model.solve_time}
        Semantic validation: {validation_result}
        *******************************************""")
        encoding_components = decompose_full_polished_definition(encoding)
        model.objective = encoding_components["objective"]
        model.constraints = encoding_components["constraints"]
        return model

    def _validate_model(self, model: PolishModel, solution_model):
        # Validate minizinc solution
        task = {}
        if model.constants:
            vars = {}
            for variable in model.constants:
                vars.update({variable["variable_name"]:
                                 _split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[
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
        elites = [model for model in self.models if model.objective_val == self.min_objective_val]
        if top_n is not None: elites = self.elites[:top_n]
        return elites

def main():
    polishSomething = AlgoPolish(file_path="models/optDSL_models_2026-01-23_17-46.json")
    polishSomething.mutate()


if __name__ == "__main__":
    main()
