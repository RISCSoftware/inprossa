import constants
from constants import DEBUG_MODE_ON
from prompt_generation_utils import create_and_send_prompt_for_strictly_iterative_approach, \
    enter_variable_definitions_feedback_loop, LOOP_OF_DOOM_MAX_IT, send_feedback
from structures_utils import TreeNode, RootNode, ObjectsNode, remove_programming_environment, VariablesConstantsNode, \
    ObjectiveNode, ConstraintsNode, State


class Tree:
    def __init__(self, problem_description: list[str], llm):
        self.root = RootNode()
        self.problem_description = problem_description
        self.llm = llm

    def dfs(self, cur_node: TreeNode):
        if cur_node.is_terminal:
            return
        while len(cur_node.get_correct_children()) < 2:
            if DEBUG_MODE_ON: print(f"""
.....................................................
Given:
{cur_node.get_partial_formulation_up_until_now()}
Create {len(cur_node.get_correct_children())}. node at level {cur_node.level+1}
.....................................................
""")
            new_child_node = None
            match cur_node.level:
                case 0:
                    new_child_node = self.create_objects_node(cur_node)
                case 1:
                    new_child_node = self.create_constants_node(cur_node)
                case 2:
                    if not cur_node.all_variables_created:
                        new_child_node = self.create_decision_variables(cur_node)
                    else:
                        new_child_node = self.create_objective_node(cur_node)
                case 3:
                    new_child_node = self.create_constraints_node(cur_node)
            if DEBUG_MODE_ON: print(f"Successfully created node: {new_child_node.id}")
            if new_child_node.state == State.CORRECT: self.dfs(new_child_node)

    def create_full_tree_with_dfs(self):
        self.dfs(self.root)
        return self.root


    def create_objects_node(self, parent: RootNode):
        # Query object types, data types
        datatypes_node = ObjectsNode(parent=parent)
        response = remove_programming_environment(
                create_and_send_prompt_for_strictly_iterative_approach(datatypes_node,
                                                                       llm=self.llm,
                                                                       full_problem_description=self.problem_description))
        response = enter_variable_definitions_feedback_loop(datatypes_node,
                                                            response,
                                                            llm=self.llm,
                                                            full_problem_description=self.problem_description)
        datatypes_node.set_content(response)
        # send_feedback(datatypes_node)
        # print(f"*** Response, global problem/datatypes: {response}\n")
        if response == "":
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
            response = remove_programming_environment(
                create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node,
                                                                       llm=self.llm,
                                                                       full_problem_description=self.problem_description))
            response = enter_variable_definitions_feedback_loop(constants_variables_node,
                                                                response,
                                                                llm=self.llm,
                                                                full_problem_description=self.problem_description)
            successfully_added = constants_variables_node.set_constants(response)
            i += 1
        # send_feedback(constants_variables_node)
        # print(f"*** Response, constants: {response}\n")
        if response == "" or i == LOOP_OF_DOOM_MAX_IT:
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
            successfully_added = constants_variables_node.set_variables(response)
            i += 1
        # send_feedback(constants_variables_node)
        # print(f"*** Response (decision) variables: {response}\n")
        if response == "" or i == LOOP_OF_DOOM_MAX_IT:
            print("Creating decision variables failed!")
        else:
            print(f"Creating decision variables succeeded: {response}")
        return constants_variables_node

    def create_objective_node(self, parent: VariablesConstantsNode):
        # Query objective function
        obj_function_node = ObjectiveNode(parent=parent)
        response = remove_programming_environment(
            create_and_send_prompt_for_strictly_iterative_approach(obj_function_node,
                                                                   llm=self.llm,
                                                                   full_problem_description=self.problem_description))
        response = enter_variable_definitions_feedback_loop(obj_function_node,
                                                            response,
                                                            llm=self.llm,
                                                            full_problem_description=self.problem_description)
        obj_function_node.set_content(response)
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
            response = remove_programming_environment(
                create_and_send_prompt_for_strictly_iterative_approach(constraints_node,
                                                                       llm=self.llm,
                                                                       subproblem_description=self.problem_description[i]))
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
                send_feedback(constraints_node, llm=self.llm)
        if constants.DEBUG_MODE_ON: print(f"""Full formulation:
        {constraints_node.get_partial_formulation_up_until_now()}
----------------------------------------------------------------------------""")
        return constraints_node

d2_bin_packing_formalized_problem_description = [
    # Input
    """
    Input
    ´´´ json
    {
        "BOX_HEIGHT": 6,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1"
                "width": 4,
                "height": 3
            },
            {
                "name": "item2",
                "width": 3,
                "height": 2
            },
            {
                "name": "item3",
                "width": 5,
                "height": 3
            },
            {
                "name": "item4",
                "width": 2,
                "height": 4
            },
            {
                "name": "item5",
                "width": 3,
                "height": 3
            },
            {
                "name": "item6",
                "width": 5,
                "height": 2
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    Output:
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "mandatory_variable_name": "item_box_assignment",
            "suggested_shape": "array of objects or multiple arrays"
        },
        {
            "description": "Position x and y of each item within box",
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array of objects or multiple arrays"
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
        - the assigment of each item into a box and 
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

if __name__ == "__main__":
    llm = constants.LLM
    tree = Tree(d2_bin_packing_formalized_problem_description, llm)
    tree.create_full_tree_with_dfs()
    print(tree.root)