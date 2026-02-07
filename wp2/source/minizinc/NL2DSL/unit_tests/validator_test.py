import json
import unittest

from BinPackingValidator import UnsatisfiableProblemError, check_satisfiability_given, validate_solution
from input_reader import InputReader
from structures_utils import remove_programming_environment
from tree_search_dfs import DfsTree


class TestValidator(unittest.TestCase):

    def test_unsatisfiability_of_variables(self):
        with self.assertRaises(UnsatisfiableProblemError):
            check_satisfiability_given([
            {
                "description": "",
                "variable_name": "BOX_HEIGHT",
                "type": "BOX_HEIGHT : int",
                "variable_instance": [
                    5
                ],
                "variable_dslcode_template": "BOX_HEIGHT : int = {}",
                "initialization": "BOX_HEIGHT : int = 5"
            },
            {
                "description": "",
                "variable_name": "BOX_WIDTH",
                "type": "BOX_WIDTH : int",
                "variable_instance": [
                    12
                ],
                "variable_dslcode_template": "BOX_WIDTH : int = {}",
                "initialization": "BOX_WIDTH : int = 12"
            },
            {
                "description": "",
                "variable_name": "ITEMS",
                "type": "ITEMS : DSList(length = {}, elem_type = Item)",
                "variable_instance": [
                    3,
                    [
                        {
                            "name": "item1",
                            "width": 4,
                            "height": 3
                        },
                        {
                            "name": "item2",
                            "width": 1,
                            "height": 2
                        },
                        {
                            "name": "item3",
                            "width": 35,
                            "height": 3
                        }
                    ],
                    3
                ],
                "variable_dslcode_template": "ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}",
                "initialization": "ITEMS : Annotated[list[Item], Len(9, 9)] = [{'name': 'item1', 'width': 4, 'height': 3}, {'name': 'item2', 'width': 1, 'height': 2}, {'name': 'item3', 'width': 5, 'height': 3}, {'name': 'item4', 'width': 4, 'height': 2}, {'name': 'item5', 'width': 1, 'height': 3}, {'name': 'item6', 'width': 5, 'height': 2}, {'name': 'item7', 'width': 9, 'height': 5}, {'name': 'item8', 'width': 3, 'height': 5}, {'name': 'item9', 'width': 5, 'height': 1}]\nN_ITEMS : int = 9"
            }
        ])
        with self.assertRaises(UnsatisfiableProblemError):
            check_satisfiability_given([
                {
                    "description": "",
                    "variable_name": "BOX_HEIGHT",
                    "type": "BOX_HEIGHT : int",
                    "variable_instance": [
                        5
                    ],
                    "variable_dslcode_template": "BOX_HEIGHT : int = {}",
                    "initialization": "BOX_HEIGHT : int = 5"
                },
                {
                    "description": "",
                    "variable_name": "BOX_WIDTH",
                    "type": "BOX_WIDTH : int",
                    "variable_instance": [
                        12
                    ],
                    "variable_dslcode_template": "BOX_WIDTH : int = {}",
                    "initialization": "BOX_WIDTH : int = 12"
                },
                {
                    "description": "",
                    "variable_name": "ITEMS",
                    "type": "ITEMS : DSList(length = {}, elem_type = Item)",
                    "variable_instance": [
                        3,
                        [
                            {
                                "name": "item1",
                                "width": 4,
                                "height": 3
                            },
                            {
                                "name": "item2",
                                "width": 1,
                                "height": 20
                            },
                            {
                                "name": "item3",
                                "width": 1,
                                "height": 3
                            }
                        ],
                        3
                    ],
                    "variable_dslcode_template": "ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}",
                    "initialization": "ITEMS : Annotated[list[Item], Len(9, 9)] = [{'name': 'item1', 'width': 4, 'height': 3}, {'name': 'item2', 'width': 1, 'height': 2}, {'name': 'item3', 'width': 5, 'height': 3}, {'name': 'item4', 'width': 4, 'height': 2}, {'name': 'item5', 'width': 1, 'height': 3}, {'name': 'item6', 'width': 5, 'height': 2}, {'name': 'item7', 'width': 9, 'height': 5}, {'name': 'item8', 'width': 3, 'height': 5}, {'name': 'item9', 'width': 5, 'height': 1}]\nN_ITEMS : int = 9"
                }
            ])
        with self.assertRaises(ValueError):
            check_satisfiability_given([
                {
                    "description": "",
                    "variable_name": "BOX_HEIGHT",
                    "type": "BOX_HEIGHT : int",
                    "variable_instance": [
                        5
                    ],
                    "variable_dslcode_template": "BOX_HEIGHT : int = {}",
                    "initialization": "BOX_HEIGHT : int = 5"
                },
                {
                    "description": "",
                    "variable_name": "BOX_WIDTH",
                    "type": "BOX_WIDTH : int",
                    "variable_instance": [
                        12
                    ],
                    "variable_dslcode_template": "BOX_WIDTH : int = {}",
                    "initialization": "BOX_WIDTH : int = 12"
                },
                {
                    "description": "",
                    "variable_name": "ITEMS",
                    "type": "ITEMS : DSList(length = {}, elem_type = Item)",
                    "variable_instance": [
                        3,
                        [
                            {
                                "name": "item1",
                                "width": 4,
                                "height": -3
                            },
                            {
                                "name": "item2",
                                "width": 1,
                                "height": 2
                            },
                            {
                                "name": "item3",
                                "width": 35,
                                "height": 3
                            }
                        ],
                        3
                    ],
                    "variable_dslcode_template": "ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}",
                    "initialization": "ITEMS : Annotated[list[Item], Len(9, 9)] = [{'name': 'item1', 'width': 4, 'height': 3}, {'name': 'item2', 'width': 1, 'height': 2}, {'name': 'item3', 'width': 5, 'height': 3}, {'name': 'item4', 'width': 4, 'height': 2}, {'name': 'item5', 'width': 1, 'height': 3}, {'name': 'item6', 'width': 5, 'height': 2}, {'name': 'item7', 'width': 9, 'height': 5}, {'name': 'item8', 'width': 3, 'height': 5}, {'name': 'item9', 'width': 5, 'height': 1}]\nN_ITEMS : int = 9"
                }
            ])

    def test_unsatisfiability_of_constants_with_tree(self):
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            "problem_descriptions/2d_bin_packing_unsat_constants.json",
           "problem_descriptions/2d_bin_packing_inst_1_without_inoutput.json",
            "fixed_objects_fixed_inoutput_values")
        tree = DfsTree(None,
                problem_description=problem_description,
                objects_spec=objects,
                input_variable_spec=intput_variable_spec,
                output_variable_spec=output_variable_spec)
        with self.assertRaises(UnsatisfiableProblemError):
            tree.dfs(tree.root)

    d2_bin_packing_instance = [
        # Input
        """
        ´´´ json
        {
            "BOX_HEIGHT": 4,
            "BOX_WIDTH": 4,
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
                    "width": 1,
                    "height": 1
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

    def test_invalid_solution_validation(self):
        task = {
            "input": json.loads(remove_programming_environment(self.d2_bin_packing_instance[0])),
            "output": json.loads(remove_programming_environment(self.d2_bin_packing_instance[1]))
        }
        # Validate solver solutions
        # Invalid objective value
        with self.assertRaises(AssertionError) as cm:
            validate_solution(json.loads(
                "{\"objective\": [0, 1, 1, 8], \"nr_used_boxes\": [1], \"item_box_assignments\": [[3, 2, 1]], \"x_y_positions\": [[{\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 3, \"x\": 0, \"y\": 0}]]}"),
                          task)
        self.assertEqual(str(cm.exception), "Invalid value for objective, more boxes than items: 8")

        # Invalid objective value
        with self.assertRaises(AssertionError) as cm:
            validate_solution(json.loads(
                "{\"objective\": [0, 1], \"nr_used_boxes\": [1], \"item_box_assignments\": [[3, 2, 1]], \"x_y_positions\": [[{\"box_id\": 3, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 2, \"item_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 0, \"x\": 0, \"y\": 0}]]}"),
                task)
        self.assertEqual(str(cm.exception), "Invalid value for objective, max_box_id and said value do not match.")

        # Exceeds box boundaries
        with self.assertRaises(AssertionError) as cm:
            validate_solution(json.loads(
                "{\"objective\": [0, 1, 1, 3], \"nr_used_boxes\": [1], \"item_box_assignments\": [[3, 2, 1]], \"x_y_positions\": [[{\"box_id\": 3, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 2, \"item_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 3, \"x\": 0, \"y\": 0}]]}"),
                task)
        self.assertEqual(str(cm.exception), "Item placement 8 exceeds box width 4")

        # Items 0 and 1 overlap
        with self.assertRaises(AssertionError) as cm:
            validate_solution(json.loads(
                "{\"objective\": [0, 1, 1, 2], \"nr_used_boxes\": [1], \"item_box_assignments\": [[1, 2, 2]], \"x_y_positions\": [[{\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 3, \"x\": 0, \"y\": 0}]]}"),
                task)
        self.assertEqual(str(cm.exception), "Items 1 and 2 overlap.")

    def test_valid_solution_validation(self):
        task = {
            "input": json.loads(remove_programming_environment(self.d2_bin_packing_instance[0])),
            "output": json.loads(remove_programming_environment(self.d2_bin_packing_instance[1]))
        }
        validate_solution(json.loads(
            "{\"objective\": [0, 1, 1, 2], \"nr_used_boxes\": [1], \"item_box_assignments\": [[1, 2, 2]], \"x_y_positions\": [[{\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 3, \"x\": 3, \"y\": 0}]]}"),
            task)

    def test_strange_case(self):
        d2_bin_packing_formalized_problem_description_inst2 = [
            # Input
            """
            ´´´ json
            {
                "BOX_HEIGHT": 5,
                "BOX_WIDTH": 12,
                "ITEMS": [
                    {
                        "width": 4,
                        "height": 3
                    },
                    {
                        "width": 1,
                        "height": 2
                    },
                    {
                        "width": 5,
                        "height": 3
                    },
                    {
                        "width": 4,
                        "height": 2
                    },
                    {
                        "width": 1,
                        "height": 3
                    },
                    {
                        "width": 9,
                        "height": 2
                    },
                    {
                        "width": 9,
                        "height": 5
                    },
                    {
                        "width": 3,
                        "height": 5
                    },
                    {
                        "width": 5,
                        "height": 1
                    }
                ]
            }´´´
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
            """
        ]

        # Example of calling from another function:
        task = {
            "input": json.loads(
                remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[0])),
            "output": json.loads(
                remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[1]))
        }
        # Validate solver solutions
        print(validate_solution(json.loads(
            "{\"nr_used_boxes\": [1], \"item_box_assignments\": [[{\"box_id\": 3, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}]], \"x_y_positions\": [[{\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}]], \"objective\": [8]}"),
            task))
