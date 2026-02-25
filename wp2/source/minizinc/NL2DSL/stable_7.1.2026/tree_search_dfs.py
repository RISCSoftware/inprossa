
import constants
from constants import DEBUG_MODE_ON
from structures_utils import TreeNode, VariablesConstantsNode, State
from tree_search_base import TreeBase


class DfsTree(TreeBase):
    NR_MAX_CHILDREN = 1

    def dfs(self, cur_node: TreeNode):
        if (cur_node.state == State.FAILED
                or cur_node.n_failed_generations != 0
                or cur_node.is_terminal):
            return
        while len(cur_node.get_correct_children()) < DfsTree.NR_MAX_CHILDREN:
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
                    if (isinstance(cur_node, VariablesConstantsNode) and
                            not cur_node.all_variables_created):
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


d2_bin_packing_formalized_problem_description_inst2 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 6,
        "BOX_WIDTH": 10,
        "ITEMS": [
            ,
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
new_constants = """
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
    """

if __name__ == "__main__":
    llm = constants.get_LLM_client()
    #tree = DfsTree(llm, problem_description=d2_bin_packing_formalized_problem_description_inst2)
    #tree.create_full_tree_with_dfs()

    tree = DfsTree(llm)
    tree.use_given_model_with_input("optDSL_model_2026-01-07_14.json")

    print(tree.root)
