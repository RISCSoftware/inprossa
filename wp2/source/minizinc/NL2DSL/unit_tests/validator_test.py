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

    def test_case1(self):
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
        try:
            print(validate_solution(json.loads(
                "{\"nr_used_boxes\": [1], \"item_box_assignments\": [[{\"box_id\": 3, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}]], \"x_y_positions\": [[{\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"x\": 0, \"y\": 0}]], \"objective\": [8]}"),
                task))
        except Exception as e:
            raise AssertionError(e)

    def test_case2(self):
        d2_bin_packing_formalized_problem_description_inst2 = [
            # Input
            """
            ´´´ json
            {
                "BOX_HEIGHT": 10,
                "BOX_WIDTH": 8,
                "ITEMS": [
                    {
                        "width": 1,
                        "height": 4
                    },
                    {
                        "width": 3,
                        "height": 1
                    },
                    {
                        "width": 8,
                        "height": 7
                    },
                    {
                        "width": 7,
                        "height": 10
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
        try:
            print(validate_solution(json.loads(
                "{\"nr_used_boxes\": [3], \"item_box_assignments\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"x_y_positions\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"objective\": [3], \"assignments__calculate_objective__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__calculate_objective__1\": [3, 2, 2, 1], \"max_box_id__calculate_objective__1\": [0, 3, 3, 3, 3], \"assignments__items_fit_exactly_in_boxes__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__items_fit_exactly_in_boxes__1\": [3, 2, 2, 1], \"item_height__items_fit_exactly_in_boxes__1\": [4, 1, 7, 10], \"item_id__items_fit_exactly_in_boxes__1\": [1, 2, 3, 4], \"item_width__items_fit_exactly_in_boxes__1\": [1, 3, 8, 7], \"items__items_fit_exactly_in_boxes__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]], \"pos_x__items_fit_exactly_in_boxes__1\": [0, 0, 0, 0], \"pos_y__items_fit_exactly_in_boxes__1\": [0, 7, 0, 0], \"positions__items_fit_exactly_in_boxes__1\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"assignments__no_overlap__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"hi__no_overlap__1\": [1], \"hj__no_overlap__1\": [7], \"items__no_overlap__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]], \"positions__no_overlap__1\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"wi__no_overlap__1\": [3], \"wj__no_overlap__1\": [8], \"xi__no_overlap__1\": [0], \"xj__no_overlap__1\": [0], \"yi__no_overlap__1\": [7], \"yj__no_overlap__1\": [0], \"assignments__ensure_item_box_assignment_validity__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__ensure_item_box_assignment_validity__1\": [3, 2, 2, 1], \"item_id__ensure_item_box_assignment_validity__1\": [1, 2, 3, 4], \"items__ensure_item_box_assignment_validity__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]]}"),
                task))
        except Exception as e:
            raise AssertionError(e)

    def test_case3(self):
        d2_bin_packing_formalized_problem_description_inst2 = [
            # Input
            """
            ´´´ json
            {
                "BOX_HEIGHT": 10,
                "BOX_WIDTH": 8,
                "ITEMS": [
                    {
                        "width": 1,
                        "height": 4
                    },
                    {
                        "width": 3,
                        "height": 1
                    },
                    {
                        "width": 8,
                        "height": 7
                    },
                    {
                        "width": 7,
                        "height": 10
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
        try:
            validate_solution(json.loads(
                "{\"nr_used_boxes\": [3], \"item_box_assignments\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"x_y_positions\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"objective\": [3], \"assignments__calculate_objective__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__calculate_objective__1\": [3, 2, 2, 1], \"max_box_id__calculate_objective__1\": [0, 3, 3, 3, 3], \"assignments__items_fit_exactly_in_boxes__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__items_fit_exactly_in_boxes__1\": [3, 2, 2, 1], \"item_height__items_fit_exactly_in_boxes__1\": [4, 1, 7, 10], \"item_id__items_fit_exactly_in_boxes__1\": [1, 2, 3, 4], \"item_width__items_fit_exactly_in_boxes__1\": [1, 3, 8, 7], \"items__items_fit_exactly_in_boxes__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]], \"pos_x__items_fit_exactly_in_boxes__1\": [0, 0, 0, 0], \"pos_y__items_fit_exactly_in_boxes__1\": [0, 7, 0, 0], \"positions__items_fit_exactly_in_boxes__1\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"assignments__no_overlap__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"hi__no_overlap__1\": [1], \"hj__no_overlap__1\": [7], \"items__no_overlap__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]], \"positions__no_overlap__1\": [[{\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 7}, {\"x\": 0, \"y\": 0}, {\"x\": 0, \"y\": 0}]], \"wi__no_overlap__1\": [3], \"wj__no_overlap__1\": [8], \"xi__no_overlap__1\": [0], \"xj__no_overlap__1\": [0], \"yi__no_overlap__1\": [7], \"yj__no_overlap__1\": [0], \"assignments__ensure_item_box_assignment_validity__1\": [[{\"box_id\": 3, \"item_id\": 1}, {\"box_id\": 2, \"item_id\": 2}, {\"box_id\": 2, \"item_id\": 3}, {\"box_id\": 1, \"item_id\": 4}]], \"box_id__ensure_item_box_assignment_validity__1\": [3, 2, 2, 1], \"item_id__ensure_item_box_assignment_validity__1\": [1, 2, 3, 4], \"items__ensure_item_box_assignment_validity__1\": [[{\"height\": 4, \"width\": 1}, {\"height\": 1, \"width\": 3}, {\"height\": 7, \"width\": 8}, {\"height\": 10, \"width\": 7}]]}"),
                task)
        except Exception as e:
            raise AssertionError(e)

    def test_fail_exceeds_box_boundaries(self):
        d2_bin_packing_formalized_problem_description_inst2 = [
            # Input
            """
            ´´´ json
            {
                "BOX_HEIGHT": 15,
                "BOX_WIDTH": 20,
                "ITEMS": [
                    {
                        "width": 20,
                        "height": 9
                    },
                    {
                        "width": 17,
                        "height": 6
                    },
                    {
                        "width": 18,
                        "height": 5
                    },
                    {
                        "width": 13,
                        "height": 1
                    },
                    {
                        "width": 18,
                        "height": 12
                    },
                    {
                        "width": 18,
                        "height": 15
                    },
                    {
                        "width": 4,
                        "height": 11
                    },
                    {
                        "width": 13,
                        "height": 7
                    },
                    {
                        "width": 8,
                        "height": 1
                    },
                    {
                        "width": 19,
                        "height": 9
                    },
                    {
                        "width": 20,
                        "height": 6
                    },
                    {
                        "width": 17,
                        "height": 8
                    },
                    {
                        "width": 11,
                        "height": 9
                    },
                    {
                        "width": 11,
                        "height": 14
                    },
                    {
                        "width": 8,
                        "height": 14
                    },
                    {
                        "width": 14,
                        "height": 8
                    },
                    {
                        "width": 4,
                        "height": 9
                    },
                    {
                        "width": 15,
                        "height": 14
                    },
                    {
                        "width": 18,
                        "height": 12
                    },
                    {
                        "width": 3,
                        "height": 8
                    },
                    {
                        "width": 11,
                        "height": 10
                    },
                    {
                        "width": 8,
                        "height": 10
                    },
                    {
                        "width": 14,
                        "height": 3
                    },
                    {
                        "width": 14,
                        "height": 8
                    },
                    {
                        "width": 6,
                        "height": 8
                    },
                    {
                        "width": 20,
                        "height": 1
                    },
                    {
                        "width": 12,
                        "height": 1
                    },
                    {
                        "width": 15,
                        "height": 14
                    },
                    {
                        "width": 19,
                        "height": 14
                    },
                    {
                        "width": 9,
                        "height": 4
                    },
                    {
                        "width": 12,
                        "height": 4
                    },
                    {
                        "width": 5,
                        "height": 6
                    },
                    {
                        "width": 10,
                        "height": 10
                    },
                    {
                        "width": 12,
                        "height": 12
                    },
                    {
                        "width": 18,
                        "height": 15
                    },
                    {
                        "width": 5,
                        "height": 4
                    },
                    {
                        "width": 3,
                        "height": 12
                    },
                    {
                        "width": 13,
                        "height": 15
                    },
                    {
                        "width": 16,
                        "height": 11
                    },
                    {
                        "width": 8,
                        "height": 2
                    },
                    {
                        "width": 5,
                        "height": 9
                    },
                    {
                        "width": 9,
                        "height": 6
                    },
                    {
                        "width": 19,
                        "height": 4
                    },
                    {
                        "width": 13,
                        "height": 13
                    },
                    {
                        "width": 9,
                        "height": 9
                    },
                    {
                        "width": 13,
                        "height": 14
                    },
                    {
                        "width": 13,
                        "height": 14
                    },
                    {
                        "width": 12,
                        "height": 2
                    },
                    {
                        "width": 16,
                        "height": 4
                    },
                    {
                        "width": 10,
                        "height": 10
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
        self.assertRaises(AssertionError, validate_solution, json.loads(
                "{\"nr_used_boxes\": [46], \"item_box_assignments\": [[{\"box_id\": 45, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 41, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 40, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 39, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 38, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 37, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 46, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 36, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 35, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 34, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 33, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 31, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 30, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 29, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 28, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 27, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 26, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 25, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 24, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 23, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 22, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 44, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 21, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 20, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 19, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 18, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 17, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 16, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 43, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 15, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 14, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 13, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 42, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 12, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 10, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 9, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"x_y_positions\": [[{\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"objective\": [46], \"assignments__calculate_objective__1\": [[{\"box_id\": 45, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 41, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 40, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 39, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 38, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 37, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 46, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 36, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 35, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 34, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 33, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 31, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 30, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 29, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 28, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 27, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 26, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 25, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 24, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 23, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 22, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 44, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 21, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 20, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 19, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 18, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 17, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 16, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 43, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 15, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 14, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 13, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 42, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 12, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 10, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 9, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"max_box_id__calculate_objective__1\": [0, 45, 45, 45, 45, 45, 45, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46, 46], \"assigned_x__items_fit_exactly_in_boxes__1\": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 5, 0, 4, 0], \"assigned_y__items_fit_exactly_in_boxes__1\": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], \"assignments__items_fit_exactly_in_boxes__1\": [[{\"box_id\": 45, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 41, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 40, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 39, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 38, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 37, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 46, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 36, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 35, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 34, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 33, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 31, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 30, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 29, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 28, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 27, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 26, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 25, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 24, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 23, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 22, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 44, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 21, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 20, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 19, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 18, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 17, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 16, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 43, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 15, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 14, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 13, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 42, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 12, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 10, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 9, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"item_height__items_fit_exactly_in_boxes__1\": [9, 6, 5, 1, 12, 15, 11, 7, 1, 9, 6, 8, 9, 14, 14, 8, 9, 14, 12, 8, 10, 10, 3, 8, 8, 1, 1, 14, 14, 4, 4, 6, 10, 12, 15, 4, 12, 15, 11, 2, 9, 6, 4, 13, 9, 14, 14, 2, 4, 10], \"item_width__items_fit_exactly_in_boxes__1\": [20, 17, 18, 13, 18, 18, 4, 13, 8, 19, 20, 17, 11, 11, 8, 14, 4, 15, 18, 3, 11, 8, 14, 14, 6, 20, 12, 15, 19, 9, 12, 5, 10, 12, 18, 5, 3, 13, 16, 8, 5, 9, 19, 13, 9, 13, 13, 12, 16, 10], \"items__items_fit_exactly_in_boxes__1\": [[{\"height\": 9, \"width\": 20}, {\"height\": 6, \"width\": 17}, {\"height\": 5, \"width\": 18}, {\"height\": 1, \"width\": 13}, {\"height\": 12, \"width\": 18}, {\"height\": 15, \"width\": 18}, {\"height\": 11, \"width\": 4}, {\"height\": 7, \"width\": 13}, {\"height\": 1, \"width\": 8}, {\"height\": 9, \"width\": 19}, {\"height\": 6, \"width\": 20}, {\"height\": 8, \"width\": 17}, {\"height\": 9, \"width\": 11}, {\"height\": 14, \"width\": 11}, {\"height\": 14, \"width\": 8}, {\"height\": 8, \"width\": 14}, {\"height\": 9, \"width\": 4}, {\"height\": 14, \"width\": 15}, {\"height\": 12, \"width\": 18}, {\"height\": 8, \"width\": 3}, {\"height\": 10, \"width\": 11}, {\"height\": 10, \"width\": 8}, {\"height\": 3, \"width\": 14}, {\"height\": 8, \"width\": 14}, {\"height\": 8, \"width\": 6}, {\"height\": 1, \"width\": 20}, {\"height\": 1, \"width\": 12}, {\"height\": 14, \"width\": 15}, {\"height\": 14, \"width\": 19}, {\"height\": 4, \"width\": 9}, {\"height\": 4, \"width\": 12}, {\"height\": 6, \"width\": 5}, {\"height\": 10, \"width\": 10}, {\"height\": 12, \"width\": 12}, {\"height\": 15, \"width\": 18}, {\"height\": 4, \"width\": 5}, {\"height\": 12, \"width\": 3}, {\"height\": 15, \"width\": 13}, {\"height\": 11, \"width\": 16}, {\"height\": 2, \"width\": 8}, {\"height\": 9, \"width\": 5}, {\"height\": 6, \"width\": 9}, {\"height\": 4, \"width\": 19}, {\"height\": 13, \"width\": 13}, {\"height\": 9, \"width\": 9}, {\"height\": 14, \"width\": 13}, {\"height\": 14, \"width\": 13}, {\"height\": 2, \"width\": 12}, {\"height\": 4, \"width\": 16}, {\"height\": 10, \"width\": 10}]], \"assignments__no_overlap_in_boxes__1\": [[{\"box_id\": 45, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 41, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 40, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 39, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 38, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 37, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 46, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 36, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 35, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 34, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 33, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 31, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 30, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 29, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 28, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 27, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 26, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 25, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 24, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 23, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 22, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 44, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 21, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 20, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 19, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 18, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 17, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 16, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 43, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 15, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 14, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 13, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 42, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 12, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 10, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 9, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"assignments__each_item_in_one_box__1\": [[{\"box_id\": 45, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 41, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 40, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 39, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 38, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 37, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 46, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 36, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 35, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 34, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 33, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 31, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 30, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 29, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 28, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 27, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 26, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 32, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 25, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 24, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 23, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 22, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 44, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 21, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 20, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 19, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 18, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 17, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 16, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 43, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 15, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 14, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 13, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 42, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 12, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 11, \"item_id\": 1, \"x\": 3, \"y\": 0}, {\"box_id\": 10, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 9, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 8, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 7, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 6, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 5, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 4, \"item_id\": 1, \"x\": 5, \"y\": 0}, {\"box_id\": 3, \"item_id\": 1, \"x\": 0, \"y\": 0}, {\"box_id\": 2, \"item_id\": 1, \"x\": 4, \"y\": 0}, {\"box_id\": 1, \"item_id\": 1, \"x\": 0, \"y\": 0}]], \"items__each_item_in_one_box__1\": [[{\"height\": 9, \"width\": 20}, {\"height\": 6, \"width\": 17}, {\"height\": 5, \"width\": 18}, {\"height\": 1, \"width\": 13}, {\"height\": 12, \"width\": 18}, {\"height\": 15, \"width\": 18}, {\"height\": 11, \"width\": 4}, {\"height\": 7, \"width\": 13}, {\"height\": 1, \"width\": 8}, {\"height\": 9, \"width\": 19}, {\"height\": 6, \"width\": 20}, {\"height\": 8, \"width\": 17}, {\"height\": 9, \"width\": 11}, {\"height\": 14, \"width\": 11}, {\"height\": 14, \"width\": 8}, {\"height\": 8, \"width\": 14}, {\"height\": 9, \"width\": 4}, {\"height\": 14, \"width\": 15}, {\"height\": 12, \"width\": 18}, {\"height\": 8, \"width\": 3}, {\"height\": 10, \"width\": 11}, {\"height\": 10, \"width\": 8}, {\"height\": 3, \"width\": 14}, {\"height\": 8, \"width\": 14}, {\"height\": 8, \"width\": 6}, {\"height\": 1, \"width\": 20}, {\"height\": 1, \"width\": 12}, {\"height\": 14, \"width\": 15}, {\"height\": 14, \"width\": 19}, {\"height\": 4, \"width\": 9}, {\"height\": 4, \"width\": 12}, {\"height\": 6, \"width\": 5}, {\"height\": 10, \"width\": 10}, {\"height\": 12, \"width\": 12}, {\"height\": 15, \"width\": 18}, {\"height\": 4, \"width\": 5}, {\"height\": 12, \"width\": 3}, {\"height\": 15, \"width\": 13}, {\"height\": 11, \"width\": 16}, {\"height\": 2, \"width\": 8}, {\"height\": 9, \"width\": 5}, {\"height\": 6, \"width\": 9}, {\"height\": 4, \"width\": 19}, {\"height\": 13, \"width\": 13}, {\"height\": 9, \"width\": 9}, {\"height\": 14, \"width\": 13}, {\"height\": 14, \"width\": 13}, {\"height\": 2, \"width\": 12}, {\"height\": 4, \"width\": 16}, {\"height\": 10, \"width\": 10}]]}"),
                task)
