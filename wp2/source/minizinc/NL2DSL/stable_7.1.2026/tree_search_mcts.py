from copy import deepcopy

from structures_utils import TreeNode, VariablesConstantsNode
from tree_search_base import TreeBase
from CONSTANTS import DEBUG_MODE_ON, LLM


class MctsTree(TreeBase):

    def mcts_search(self, iterations=10):
        for _ in range(iterations):
            node = self.root

            while node.parent and node.is_fully_expanded():
                node = node.best_child()

            if not node.is_terminal and not node.is_fully_expanded():
                node = self.expand(node)

            winner = self.rollout(node)
            self.backpropagate(node, winner)


    def expand(self, node: TreeNode):
        if DEBUG_MODE_ON: print(f"""
        .....................................................
        Given:
        {node.get_partial_formulation_up_until_now()}
        Create {len(node.get_correct_children())}. node at level {node.level + 1}
        .....................................................
        """)
        new_child_node = None
        match node.level:
            case 0:
                new_child_node = self.create_objects_node(node)
            case 1:
                new_child_node = self.create_constants_node(node)
            case 2:
                if (isinstance(node, VariablesConstantsNode) and
                        not node.all_variables_created):
                    new_child_node = self.create_decision_variables(self)
                else:
                    new_child_node = self.create_objective_node(self)
            case 3:
                new_child_node = self.create_constraints_node(self)
        if DEBUG_MODE_ON: print(f"Successfully created node: {new_child_node.id}")
        node.children.append(new_child_node)
        return new_child_node

    def rollout(self, node: TreeNode):
        cur_node = deepcopy(node)

        while True:
            cur_node = self.expand(cur_node)

            # Calculate reward
            if cur_node.is_terminal:
                reward = 0
                if cur_node.n_failed_generations == 0:
                    reward += 1
                    if cur_node.validated:
                        reward += 1
                        reward += cur_node.solve_time * 10
                        reward += cur_node.objective_val
                return reward
            # check winner state, originally returned 1, 2 or None

    def backpropagate(self, node: TreeNode, winner):
        node.visits += 1

        if winner is None:
            node.wins += 0.5
        else:
            node.wins += winner

        if node.parent:
            self.backpropagate(node, winner)

d2_bin_packing_formalized_problem_description_inst2 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 6,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1",
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

if __name__ == "__main__":
    llm = LLM
    tree = MctsTree(d2_bin_packing_formalized_problem_description_inst2, llm)
    tree.mcts_search()
    print(tree.root)