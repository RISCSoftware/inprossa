from datetime import datetime
import json

import constants
from BinPackingValidator import validate_solution
from prompt_generation_utils import create_and_send_prompt_for_strictly_iterative_approach, \
    enter_variable_definitions_feedback_loop, LOOP_OF_DOOM_MAX_IT, send_feedback
from structures_utils import RootNode, ObjectsNode, VariablesConstantsNode, \
    ObjectiveNode, ConstraintsNode, State, remove_programming_environment, initial_clean_up, \
    check_executability, split_at_outer_equals



class TreeBase:
    def __init__(self,
                 llm,
                 problem_description: list[str] = None,
                 save_nodes: bool = False,
                 save_model=True,
                 input_variable_spec: list[dict] = None,
                 output_variable_spec: list[dict] = None,
                 objects_spec: dict = None,
                 for_each_constraint_one_node: bool = False,
                 semantic_feedback_enabled: bool = False):
        self.root = RootNode(save_nodes=save_nodes, save_model=save_model)
        self.problem_description = problem_description
        self.llm = llm
        self.input_variable_spec = input_variable_spec
        self.output_variable_spec = output_variable_spec
        self.objects_spec = objects_spec
        self.result_models_file = f'optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H-%M")}.json'
        self.for_each_constraint_one_node = for_each_constraint_one_node
        self.semantic_feedback_enabled = semantic_feedback_enabled
        self.best_child : ConstraintsNode = None

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
            successfully_added = constants_variables_node.set_constants(response, self.problem_description[0])
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

    def create_constraints_node(self, parent: ObjectiveNode, cur_subproblem_index: int = None):
        # Query constraints
        constraints_node = ConstraintsNode(parent=parent, level=cur_subproblem_index)

        # For each constraint one node
        if self.for_each_constraint_one_node and cur_subproblem_index is not None:
            constraints_node = self._generate_constraint_code(constraints_node, cur_subproblem_index-1)
            if cur_subproblem_index < len(self.problem_description): return constraints_node
        else:
            # All constraints are saved in one node
            for i in range(3, len(self.problem_description)):
                constraints_node = self._generate_constraint_code(constraints_node, i)

        # Create connection between objective and given objective decision variable
        #objective_var_name = [variable["mandatory_variable_name"] for variable in json.loads(
        #    remove_programming_environment(self.problem_description[1])) if
        #                      variable["is_objective"]][0]
        #constraints_node.set_content(f"\n{objective_var_name} = objective\n")

        # Validate minizinc solution
        task = {}
        if self.input_variable_spec:
            vars = {}
            for variable in self.input_variable_spec:
                vars.update({variable["variable_name"]: split_at_outer_equals(variable["initialization"])[1].split("N_", 1)[0].strip()})
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
            constraints_node.state = State.FAILED
        except Exception as e:
            validation_res = f"Evaluation failed: {e}"
            constraints_node.state = State.FAILED
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
        # Save best child yet
        if constraints_node.last_in_progress:
            if self.best_child is None:
                self.best_child = constraints_node
            elif (constraints_node.state == State.CORRECT and
                constraints_node.n_failed_generations == 0 and
                constraints_node.validated and
                (constraints_node.objective_val < self.best_child.objective_val or
                 constraints_node.objective_val == self.best_child.objective_val and constraints_node.solve_time < self.best_child.solve_time)):
                self.best_child = constraints_node

        # Semantic feedback to LLM
        if (self.semantic_feedback_enabled and
            constraints_node.n_failed_generations == 0 and
            "Successfully" in validation_res and
            constraints_node.objective_val is not None):
            send_feedback(constraints_node, self.llm, full_problem_formulation=self.problem_description, syntax=False, best_child_yet=self.best_child == constraints_node)

        return constraints_node

    def _generate_constraint_code(self, constraints_node: ConstraintsNode, i: int):
        if i == len(self.problem_description) - 1:
            constraints_node.last_in_progress = True
        response = create_and_send_prompt_for_strictly_iterative_approach(constraints_node,
                                                                          llm=self.llm,
                                                                          subproblem_description=
                                                                          self.problem_description[i])
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
        if (i == len(self.problem_description) - 1 and
            constraints_node.n_failed_generations == 0 and
            constraints_node.state == State.CORRECT): send_feedback(constraints_node, llm=self.llm)
        return constraints_node
