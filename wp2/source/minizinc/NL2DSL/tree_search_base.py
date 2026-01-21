import re
from datetime import datetime
import json

import constants
from BinPackingValidator import validate_solution
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from input_reader import InputReader
from prompt_generation_utils import create_and_send_prompt_for_strictly_iterative_approach, \
    enter_variable_definitions_feedback_loop, LOOP_OF_DOOM_MAX_IT, send_feedback
from structures_utils import RootNode, ObjectsNode, VariablesConstantsNode, \
    ObjectiveNode, ConstraintsNode, State, remove_programming_environment, initial_clean_up, \
    check_executability, check_solver_executability_for_plain_model, \
    _split_at_outer_equals



class TreeBase:
    def __init__(self,
                 llm,
                 problem_description: list[str] = None,
                 save_nodes: bool = False,
                 save_model=True,
                 input_variable_spec: list[dict] = None,
                 output_variable_spec: list[dict] = None,
                 objects_spec: dict = None):
        self.root = RootNode(save_nodes=save_nodes, save_model=save_model)
        self.problem_description = problem_description
        self.llm = llm
        self.input_variable_spec = input_variable_spec
        self.output_variable_spec = output_variable_spec
        self.objects_spec = objects_spec
        self.result_models_file = f'optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.json'

    def create_objects_node(self, parent: RootNode):
        # Query object types, data types
        datatypes_node = ObjectsNode(parent=parent)
        # Fully script generated
        if ((self.objects_spec and self.input_variable_spec and self.output_variable_spec)
                or (self.objects_spec and not self.input_variable_spec and not self.output_variable_spec)):
            spec = ""
            for object_name, object_spec in self.objects_spec.items():
                spec += object_spec
            check_executability(datatypes_node, spec)
            datatypes_node.set_content(spec)
            datatypes_node.set_script_generated_objects(self.objects_spec)
            print(f"Creating object types succeeded: {self.objects_spec}")
            return datatypes_node
        # LLM generated
        response = create_and_send_prompt_for_strictly_iterative_approach(datatypes_node,
                                                                          llm=self.llm,
                                                                          full_problem_description=self.problem_description)
        response = enter_variable_definitions_feedback_loop(datatypes_node,
                                                            response,
                                                            llm=self.llm,
                                                            full_problem_description=self.problem_description)
        datatypes_node.set_llm_generated_objects(response)
        # Partially script generated
        if self.objects_spec:
            spec = ""
            for object_name, object_spec in self.objects_spec.items():
                spec += object_spec
            response += f"\n{spec}\n"
            datatypes_node.set_script_generated_objects(self.objects_spec)
        datatypes_node.set_content(response)
        # send_feedback(datatypes_node)
        # print(f"*** Response, global problem/datatypes: {response}\n")
        if response == "":
            datatypes_node.n_failed_generations += 1
            datatypes_node.state = State.FAILED
            print("Creating object types failed!")
        else:
            print(f"Creating object types succeeded: {response}")
        return datatypes_node

    def create_constants_node(self, parent: ObjectsNode):
        ### Query constants ######################################################################################
        constants_variables_node = VariablesConstantsNode(parent=parent)
        # Script generated
        if self.input_variable_spec:
            check_executability(constants_variables_node, json.dumps(self.input_variable_spec))
            constants_variables_node.set_constants(json.dumps(self.input_variable_spec))
            print(f"Creating constants succeeded: {self.input_variable_spec}")
            return constants_variables_node
        # LLM generated
        successfully_added = False
        i = 0
        while not successfully_added and i < LOOP_OF_DOOM_MAX_IT:
            response = create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node,
                                                                       llm=self.llm,
                                                                       full_problem_description=self.problem_description)
            response = enter_variable_definitions_feedback_loop(constants_variables_node,
                                                                response,
                                                                llm=self.llm,
                                                                full_problem_description=self.problem_description)
            successfully_added = constants_variables_node.set_constants(response)
            i += 1
        # send_feedback(constants_variables_node)
        # print(f"*** Response, constants: {response}\n")
        if response == "" or i == LOOP_OF_DOOM_MAX_IT:
            constants_variables_node.n_failed_generations += 1
            print("Creating constants failed!")
        else:
            print(f"Creating constants succeeded: {response}")
        return constants_variables_node

    def create_decision_variables(self, constants_variables_node: VariablesConstantsNode):
        ### Query decision variables ######################################################################################
        # Script generated
        if self.output_variable_spec:
            check_executability(constants_variables_node, json.dumps(self.output_variable_spec))
            constants_variables_node.set_variables(json.dumps(self.output_variable_spec), None)
            return constants_variables_node
        # LLM generated
        successfully_added = False
        i = 0
        while not successfully_added and i < LOOP_OF_DOOM_MAX_IT:
            response = remove_programming_environment(
                create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node,
                                                                       llm=self.llm,
                                                                       full_problem_description=self.problem_description))
            response = enter_variable_definitions_feedback_loop(constants_variables_node,
                                                                response,
                                                                llm=self.llm,
                                                                full_problem_description=self.problem_description)
            successfully_added = constants_variables_node.set_variables(response, self.problem_description[1])
            i += 1
        # send_feedback(constants_variables_node)
        # print(f"*** Response (decision) variables: {response}\n")
        if response == "" or i == LOOP_OF_DOOM_MAX_IT:
            constants_variables_node.n_failed_generations += 1
            print("Creating decision variables failed!")
        else:
            print(f"Creating decision variables succeeded: {response}")
        return constants_variables_node

    def create_objective_node(self, parent: VariablesConstantsNode):
        # Query objective function
        obj_function_node = ObjectiveNode(parent=parent)
        response = create_and_send_prompt_for_strictly_iterative_approach(obj_function_node,
                                                                   llm=self.llm,
                                                                   full_problem_description=self.problem_description)
        response = enter_variable_definitions_feedback_loop(obj_function_node,
                                                            response,
                                                            llm=self.llm,
                                                            full_problem_description=self.problem_description)

        obj_function_node.set_content(remove_programming_environment(response))
        # print(f"*** Obj. function: {response}\n")
        if response == "":
            print("Creating objective function failed!")
        else:
            print(f"Creating objective function succeeded: {response}")
        send_feedback(obj_function_node, llm=self.llm)
        return obj_function_node

    def create_constraints_node(self, parent: ObjectiveNode):
        # Query constraints
        constraints_node = ConstraintsNode(parent=parent)
        for i in range(3, len(self.problem_description)):
            if i == len(self.problem_description) - 1:
                constraints_node.last_in_progress = True
            response = create_and_send_prompt_for_strictly_iterative_approach(constraints_node,
                                                                       llm=self.llm,
                                                                       subproblem_description=self.problem_description[i])
            response = enter_variable_definitions_feedback_loop(constraints_node,
                                                                response,
                                                                llm=self.llm,
                                                                subproblem_description=self.problem_description[i])
            constraints_node.set_content(response)
            # print(f"*** Constraints: {response}\n")
            if response == "":
                print("Creating constraints failed!")
            else:
                print(f"Creating constraints succeeded: {response}")

            # Syntactic feedback to LLM
            if i == len(self.problem_description) - 1: send_feedback(constraints_node, llm=self.llm)

        # Create connection between objective and given objective decision variable
        objective_var_name = [variable["mandatory_variable_name"] for variable in json.loads(
            remove_programming_environment(self.problem_description[1])) if
                              variable["is_objective"]][0]
        constraints_node.set_content(f"\n{objective_var_name} = objective\n")

        # Validate minizinc solution
        task = {}
        if self.input_variable_spec:
            vars = {}
            for variable in self.input_variable_spec:
                vars.update({variable["variable_name"]: _split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[0].strip()})
            task.update({"input": vars})
        else:
            task.update({"input": json.loads(remove_programming_environment(self.problem_description[0]))})
        if self.output_variable_spec:
            vars = {}
            for variable in self.output_variable_spec:
                vars.update({variable["variable_name"]: variable["initialization"].split(":",1)[1].split("N_", 1)[0].strip()})
            task.update({"output": vars})
        else:
            task.update({"output": json.loads(remove_programming_environment(self.problem_description[1]))})

        try:
            validate_solution(constraints_node.solution_model, task)
        except AssertionError as e:
            validation_res = f"Failed to validate solution: {e}"
        except Exception as e:
            validation_res = f"Evaluation failed: {e}"
        else:
            validation_res = f"Successfully validated solution."
        constraints_node.save_child_to_file(validation_res, problem_description=self.problem_description, filename=self.result_models_file)

        # Print full formulation
        if constants.DEBUG_MODE_ON: print(f"""Full formulation:
{initial_clean_up(constraints_node.get_partial_formulation_up_until_now())}
**************************
Syntactic validation: {constraints_node.n_failed_generations} failed steps
Objective value: {constraints_node.objective_val}
Solution model: {constraints_node.solution_model}
Solve time (sec): {constraints_node.solve_time}
Semantic validation: {validation_res}
**************************
----------------------------------------------------------------------------""")
        # Semantic feedback to LLM
        if (constraints_node.n_failed_generations == 0 and
                "Successfully" in validation_res and
                constraints_node.objective_val is not None):
            send_feedback(constraints_node, self.llm, full_problem_formulation=self.problem_description, syntax=False)

        return constraints_node

    @staticmethod
    def use_given_model_with_input(file_path, new_instance_filename: str = None):
        return TreeBase._reuse_model_from_file(file_path, new_instance_filename=new_instance_filename)

    @staticmethod
    def _reuse_model_from_file(models_file_path: str, new_instance_filename: str):
        with open(models_file_path, "r", encoding="utf-8") as f:
            models = json.load(f)
        with open(new_instance_filename, "r", encoding="utf-8") as f:
            new_instance = json.load(f)

        updated_models = []
        # Query object types, data types
        if "objects" in new_instance:
            objects = InputReader.generate_objects_as_DSL_code(new_instance["objects"])
        # Query constants
        if "input_variables" in new_instance:
            input_variables = InputReader.update_data_by_instance(models[0]["constants"], new_instance["input_variables"], new_instance["objects"])
        # Query decision variables
        if "output_variables" in new_instance:
            output_variables = InputReader.update_data_by_instance(models[0]["decision_variables"], new_instance["output_variables"], new_instance["objects"], is_decision_var=True)

        for model in models:
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
                for match in re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*: +(DSInt\((?:.*?(?:\blb\s*=\s*)?)?(?:.*?(?:\bub\s*=\s*)?)?\)|DSFloat\((?:.*?(?:\blb\s*=\s*)?)?(?:.*?(?:\bub\s*=\s*)?)?\)|\s*DSList\s*\(\s*length\s*=\s*(\d+)\s*,\s*elem_type\s*=\s*([A-Za-z_][A-Za-z0-9_]*)(?:\(\))?\s*\))", code_def_part):
                    result = next(
                        (c for c in model["constants"] if match[0].lower() in c.get("variable_name").strip().lower()),
                        None)
                    if result is None:
                        result = next((d for d in model["decision_variables"] if
                                       match[0].lower() in d.get("variable_name").strip().lower()),
                                      None)
                    n_placeholders = result["type"].split("\n")[0].count("{}")
                    inst = result["variable_instance"][:n_placeholders]
                    code = code.replace(f"{match[0]}: {match[1]}", result["type"].split("\n")[0].format(*inst).replace(result["variable_name"], match[0].strip()))
            full_formulation = full_formulation + code
            model.update({"full_formulation": full_formulation})


            # Execute code block of full formulation
            full_formulation = initial_clean_up(full_formulation)
            # Syntax CHECK
            compile(full_formulation, "<string>", "exec")
            minizinc_model = MiniZincTranslator(full_formulation).unroll_translation()
            objective_val, solve_time, solution_model = "", 0, ""
            try:
                # Semantic CHECK
                objective_val, solve_time, solution_model = check_solver_executability_for_plain_model(minizinc_model)
            except Exception as e:
                print(str(e))

            model.update({"objective_val": objective_val})
            model.update({"solve_time": solve_time})
            model.update({"solution_model": solution_model})

            # Validate minizinc solution
            task = {}
            if model["constants"]:
                vars = {}
                for variable in model["constants"]:
                    vars.update({variable["variable_name"]:
                                     _split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[
                                         0].strip()})
                task.update({"input": vars})
            try:
                validate_solution(solution_model, task)
            except AssertionError as e:
                validation_res = f"Failed to validate solution: {e}"
            except Exception as e:
                validation_res = f"Evaluation failed: {e}"
            else:
                validation_res = f"Successfully validated solution."
            model.update({"final_evaluation_result": validation_res})

            updated_models.append(model)
        updated_models_filename = f'optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.json'
        with open(updated_models_filename, "w", encoding="utf-8") as f:
            json.dump(updated_models, f, indent=4)
        return updated_models_filename
