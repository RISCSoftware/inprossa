import os
import datetime
import json
import re

from datetime import datetime
from BinPackingValidator import validate_solution
from input_reader import InputReader
from structures_utils import initial_clean_up, check_solver_executability_for_plain_model, split_at_outer_equals
from Translator.Objects.MiniZincTranslator import MiniZincTranslator


class ModelReuser():

    @staticmethod
    def use_given_model_with_input(model: dict, new_instance_filename: str):
        with open(new_instance_filename, "r", encoding="utf-8") as f:
            new_instance = json.load(f)

        objects, input_variables, output_variables = ModelReuser._extract_new_instance_components(model, new_instance)
        model = ModelReuser._update_and_validate_model_with_new_instance(objects,
                                                                         input_variables,
                                                                         output_variables,
                                                                         model,
                                                                         new_instance)
        return model

    @staticmethod
    def use_given_models_with_input(file_path: str, new_instance_filename: str):
        return ModelReuser._reuse_models_from_file(file_path, new_instance_filename=new_instance_filename)

    @staticmethod
    def _reuse_models_from_file(models_file_path: str, new_instance_filename: str):
        with open(models_file_path, "r", encoding="utf-8") as f:
            models = json.load(f)
        with open(new_instance_filename, "r", encoding="utf-8") as f:
            new_instance = json.load(f)

        objects, input_variables, output_variables = ModelReuser._extract_new_instance_components(models[0], new_instance)

        updated_models = []
        for model in models:
            model = ModelReuser._update_and_validate_model_with_new_instance(objects,
                                                                             input_variables,
                                                                             output_variables,
                                                                             model,
                                                                             new_instance)
            updated_models.append(model)
        updated_models_filename = f'optDSL_models_reused_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.json'
        with open(os.path.join(os.path.dirname(os.path.dirname(models_file_path)), updated_models_filename), "w", encoding="utf-8") as f:
            json.dump(updated_models, f, indent=4)
        return updated_models_filename

    @staticmethod
    def _update_and_validate_model_with_new_instance(objects, input_variables, output_variables, model,
                                                     new_instance):
        model = ModelReuser._update_model_with_new_instance(objects, input_variables, output_variables, model,
                                                            new_instance)
        return ModelReuser._execute_and_validate_model(model)

    @staticmethod
    def _extract_new_instance_components(original_model, new_instance: dict):
        # Query object types, data types
        if "objects" in new_instance:
            objects = InputReader.generate_objects_as_DSL_code(new_instance["objects"])
        # Query constants
        if "input_variables" in new_instance:
            input_variables = InputReader.update_data_by_instance(original_model["constants"],
                                                                  new_instance["input_variables"],
                                                                  new_instance["objects"])
        # Query decision variables
        if "output_variables" in new_instance:
            output_variables = InputReader.update_data_by_instance(original_model["decision_variables"],
                                                                   new_instance["output_variables"],
                                                                   new_instance["objects"], is_decision_var=True)
        return objects, input_variables, output_variables

    @staticmethod
    def _update_model_with_new_instance(objects, input_variables, output_variables, model, new_instance):
        full_formulation = ""
        # Query object types, data types
        if "objects" in new_instance:
            model.update({"script_generated_objects": objects})
        for object, initialization in model["script_generated_objects"].items():
            full_formulation += initialization
        if model["llm_generated_objects"] != "null":
            full_formulation += model["llm_generated_objects"] + "\n"

        # Query constants
        if "input_variables" in new_instance:
            model.update({"constants": input_variables})
        for constant in model["constants"]:
            full_formulation += constant["initialization"] + "\n"

        # Query decision variables
        if "output_variables" in new_instance:
            model.update({"decision_variables": output_variables})
        for decision_variable in model["decision_variables"]:
            full_formulation += decision_variable["initialization"] + "\n"

        # Update method signatures of objective fun. and constraints
        code = model["objective"] + model["constraints"]
        for code_def_part in code.split("def "):
            for match in re.findall(
                r"([a-zA-Z_][a-zA-Z0-9_]*)\s*: +(DSInt\((?:.*?(?:\blb\s*=\s*)?)?(?:.*?(?:\bub\s*=\s*)?)?\)|DSFloat\((?:.*?(?:\blb\s*=\s*)?)?(?:.*?(?:\bub\s*=\s*)?)?\)|\s*DSList\s*\(\s*length\s*=\s*(\d+)\s*,\s*elem_type\s*=\s*([A-Za-z_][A-Za-z0-9_]*)(?:\(\))?\s*\))",
                code_def_part):
                result = next(
                    (c for c in model["constants"] if match[0].lower() in c.get("variable_name").strip().lower()),
                    None)
                if result is None:
                    result = next((d for d in model["decision_variables"] if
                                   match[0].lower() in d.get("variable_name").strip().lower()),
                                  None)
                n_placeholders = result["type"].split("\n")[0].count("{}")
                inst = result["variable_instance"][:n_placeholders]
                code = code.replace(f"{match[0]}: {match[1]}",
                                    result["type"].split("\n")[0].format(*inst).replace(result["variable_name"],
                                                                                        match[0].strip()))
        full_formulation = full_formulation + code
        model.update({"full_formulation": full_formulation})
        return model

    @staticmethod
    def _execute_and_validate_model(model):
        # Execute code block of full formulation
        full_formulation = initial_clean_up(model["full_formulation"])
        full_formulation = full_formulation.replace("\\n", "")
        # Syntax CHECK
        compile(full_formulation, "<string>", "exec")
        minizinc_model = MiniZincTranslator(full_formulation).unroll_translation()
        objective_val, solve_time, solution_model = "", 0, ""
        try:
            objective_val, solve_time, solution_model = check_solver_executability_for_plain_model(minizinc_model)
        except Exception as e:
            print(str(e))

        model.update({"objective_val": objective_val})
        model.update({"solve_time": solve_time})
        model.update({"solution_model": solution_model})

        # Validate minizinc solution
        # Semantic CHECK
        task = {}
        if model["constants"]:
            vars = {}
            for variable in model["constants"]:
                vars.update({variable["variable_name"]:
                                 split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[
                                     0].strip()})
            task.update({"input": vars})
        try:
            validate_solution(solution_model, task)
        except AssertionError as e:
            validation_res = f"Failed to validate solution: {e}"
            model.update({"validated": False})
        except Exception as e:
            validation_res = f"Evaluation failed: {e}"
            model.update({"validated": False})
        else:
            validation_res = f"Successfully validated solution."
            model.update({"validated": True})
        model.update({"final_evaluation_result": validation_res})
        return model
