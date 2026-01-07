import json

import constants
from BinPackingValidator import validate_solution
from prompt_generation_utils import create_and_send_prompt_for_strictly_iterative_approach, \
    enter_variable_definitions_feedback_loop, LOOP_OF_DOOM_MAX_IT, send_feedback
from structures_utils import RootNode, ObjectsNode, remove_programming_environment, VariablesConstantsNode, \
    ObjectiveNode, ConstraintsNode, State


class TreeBase:
    def __init__(self, llm, problem_description: list[str] = None, save_nodes: bool = False, save_model=True):
        self.root = RootNode(save_nodes=save_nodes, save_model=save_model)
        self.problem_description = problem_description
        self.llm = llm

    def create_objects_node(self, parent: RootNode):
        # Query object types, data types
        datatypes_node = ObjectsNode(parent=parent)
        response = create_and_send_prompt_for_strictly_iterative_approach(datatypes_node,
                                                                          llm=self.llm,
                                                                          full_problem_description=self.problem_description)
        response = enter_variable_definitions_feedback_loop(datatypes_node,
                                                            response,
                                                            llm=self.llm,
                                                            full_problem_description=self.problem_description)
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
        if i == len(self.problem_description) - 1: send_feedback(constraints_node, llm=self.llm)

        # Create connection between objective and given objective decision variable
        objective_var_name = [variable["mandatory_variable_name"] for variable in json.loads(
            remove_programming_environment(self.problem_description[1])) if
                              variable["is_objective"]][0]
        constraints_node.set_content(f"\n{objective_var_name} = objective\n")

        # Validate minizinc solution
        task = {
            "input": json.loads(remove_programming_environment(self.problem_description[0])),
            "output": json.loads(remove_programming_environment(self.problem_description[1]))
        }
        try:
            validate_solution(constraints_node.solution_model, task)
        except AssertionError as e:
            validation_res = f"Failed to validate solution: {e}"
        except Exception:
            validation_res = f"Evaluation failed."
        else:
            validation_res = f"Successfully validated solution."
        constraints_node.save_child_to_file(validation_res, problem_description=self.problem_description)

        # Print full formulation
        if constants.DEBUG_MODE_ON: print(f"""Full formulation:
        {constraints_node.get_partial_formulation_up_until_now()}
----------------------------------------------------------------------------""")
        # If fully successful and valid (syntactically + semantically) formulation created, send feedback
        #if (constraints_node.n_failed_generations == 0 and
        #        "Successfully" in validation_res and
        #        constraints_node.objective_val is not None):
        #    send_feedback(constraints_node, self.llm, full_problem_formulation=self.problem_description, syntax=False)

        return constraints_node

    def use_given_model_with_input(self, file_path, new_constant_variables: str = None):
        self._reconstruct_model_from_file(file_path, new_constant_variables=new_constant_variables)

    def _reconstruct_model_from_file(self, file_path, new_constant_variables: str = None, save_nodes: bool = False):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.problem_description = data["problem_description"]

        # Query object types, data types
        datatypes_node = ObjectsNode(parent=self.root)
        datatypes_node.set_content(str(data["objects"]))

        # Query constants
        constants_variables_node = VariablesConstantsNode(parent=datatypes_node)
        if new_constant_variables is None:
            constants_variables_node.set_constants(json.dumps(data["constants"]))
        else:
            self.problem_description[0] = new_constant_variables
            self.create_constants_node(parent=datatypes_node)

        # Query decision variables
        constants_variables_node.set_variables(json.dumps(data["decision_variables"]), self.problem_description[1])

        # Query objective function
        obj_function_node = ObjectiveNode(parent=constants_variables_node)
        obj_function_node.set_content(str(data["objective"]))

        # Query constraints
        constraints_node = ConstraintsNode(parent=obj_function_node)
        constraints_node.set_content(str(data["constraints"]))



d2_bin_packing_formalized_problem_description_inst1 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 5,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1",
                "width": 10,
                "height": 5
            },
            {
                "name": "item2",
                "width": 2,
                "height": 2
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]
