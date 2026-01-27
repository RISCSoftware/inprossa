# my_tests.py
import json
import os
import unittest

from input_reader import InputReader
from tree_search_base import TreeBase


# Test case class
class TestInputReaderAndResuse(unittest.TestCase):

    def test_flex_objects_flex_input_values(self):
        problem_description = InputReader.read_problem_description_from_file(
            "problem_descriptions/2d_bin_packing_input_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "flex_objects_fixed_input_values")
        self.assertEqual(problem_description[0], """´´´ json
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
}´´´""")
        self.assertEqual(problem_description[1], """´´´ json
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
]´´´""")
        self.assertEqual(problem_description[2], """Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.""")
        self.assertEqual(problem_description[3], """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[4], """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[5], """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")

    def test_flex_objects_fixed_input_values(self):
        problem_description = InputReader.read_problem_description_from_file(
            "problem_descriptions/2d_bin_packing_generic_input_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "flex_objects_fixed_input_values")
        self.assertEqual(problem_description[1], """´´´ json
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
]´´´""")
        self.assertEqual(problem_description[2], """Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.""")
        self.assertEqual(problem_description[3], """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[4], """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[5], """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")

    def test_fixed_objects_fixed_input_values(self):
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            "problem_descriptions/2d_bin_packing_generic_input_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "fixed_objects_fixed_input_values")
        self.assertEqual(objects, {'Item': 'Item = DSRecord({"width" : DSInt(lb=1, ub=5), "height" : DSInt(lb=1, ub=6)})\n'})
        self.assertEqual(intput_variable_spec[0], {
            'description': '',
            'initialization': 'BOX_HEIGHT : int = 6',
            'type': 'BOX_HEIGHT : int',
            'variable_dslcode_template': 'BOX_HEIGHT : int = {}',
            'variable_instance': [6],
            'variable_name': 'BOX_HEIGHT'})
        self.assertEqual(intput_variable_spec[1]["variable_name"], 'BOX_WIDTH')
        self.assertEqual(intput_variable_spec[1]["variable_dslcode_template"], 'BOX_WIDTH : int = {}')
        self.assertEqual(intput_variable_spec[2]["variable_name"], 'ITEMS')
        self.assertEqual(intput_variable_spec[2]["variable_dslcode_template"], 'ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}')
        self.assertEqual(output_variable_spec, None)

    def test_fixed_objects_fixed_output_values(self):
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            "problem_descriptions/2d_bin_packing_generic_output_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "fixed_objects_fixed_output_values")
        self.assertEqual(objects, {'X_Y_Position': 'X_Y_Position = DSRecord({"x" : DSInt(lb=0, ub=12), "y" : DSInt(lb=0, ub=5)})\n'})
        self.assertEqual(output_variable_spec[0]["variable_name"], "nr_used_boxes")
        self.assertEqual(output_variable_spec[0]["variable_dslcode_template"], 'nr_used_boxes : DSInt(lb={}, ub={})')
        self.assertEqual(output_variable_spec[1]["variable_name"], 'item_box_assignments')
        self.assertEqual(output_variable_spec[1]["variable_dslcode_template"], 'item_box_assignments : DSList(length = {}, elem_type = DSInt(lb={}, ub={}))\nN_ITEM_BOX_ASSIGNMENTS : int = {}')
        self.assertEqual(output_variable_spec[2]["variable_name"], 'x_y_positions')
        self.assertEqual(output_variable_spec[2]["variable_dslcode_template"], 'x_y_positions : DSList(length = {}, elem_type = X_Y_Position)\nN_X_Y_POSITIONS : int = {}')
        self.assertEqual(intput_variable_spec, None)
        self.assertEqual(problem_description[2], """Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.""")
        self.assertEqual(problem_description[3], """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[4], """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")
        self.assertEqual(problem_description[5], """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.""")

    def test_fixed_objects_fixed_inoutput_values(self):
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            "problem_descriptions/2d_bin_packing_generic_input_and_output_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "fixed_objects_fixed_inoutput_values")
        self.assertEqual(objects, {
            'Item': 'Item = DSRecord({"width" : DSInt(lb=1, ub=5), "height" : DSInt(lb=1, ub=6)})\n',
            'X_Y_Position': 'X_Y_Position = DSRecord({"x" : DSInt(lb=0, ub=20), "y" : DSInt(lb=0, ub=20)})\n'})
        self.assertEqual(intput_variable_spec[0], {
            'description': '',
            'initialization': 'BOX_HEIGHT : int = 6',
            'type': 'BOX_HEIGHT : int',
            'variable_dslcode_template': 'BOX_HEIGHT : int = {}',
            'variable_instance': [6],
            'variable_name': 'BOX_HEIGHT'})
        self.assertEqual(intput_variable_spec[1]["variable_name"], 'BOX_WIDTH')
        self.assertEqual(intput_variable_spec[1]["variable_dslcode_template"], 'BOX_WIDTH : int = {}')
        self.assertEqual(intput_variable_spec[2]["variable_name"], "ITEMS")
        self.assertEqual(intput_variable_spec[2]["variable_dslcode_template"], 'ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}')
        self.assertEqual(output_variable_spec[0]["variable_name"], "nr_used_boxes")
        self.assertEqual(output_variable_spec[0]["variable_dslcode_template"], 'nr_used_boxes : DSInt(lb={}, ub={})')
        self.assertEqual(output_variable_spec[1]["variable_name"], 'item_box_assignments')
        self.assertEqual(output_variable_spec[1]["variable_dslcode_template"],
                         'item_box_assignments : DSList(length = {}, elem_type = DSInt(lb={}, ub={}))\nN_ITEM_BOX_ASSIGNMENTS : int = {}')
        self.assertEqual(output_variable_spec[2]["variable_name"], 'x_y_positions')
        self.assertEqual(output_variable_spec[2]["variable_dslcode_template"],
                         'x_y_positions : DSList(length = {}, elem_type = X_Y_Position)\nN_X_Y_POSITIONS : int = {}')

    def test_fixed_objects_fixed_inoutput_values_with_file(self):
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            "problem_descriptions/2d_bin_packing_generic_and_file_input_inst_1.json",
            "problem_descriptions/2d_bin_packing_inst_1.json",
            "fixed_objects_fixed_input_values")
        self.assertEqual(objects, {
            'Item': 'Item = DSRecord({"width" : DSInt(lb=1, ub=5), "height" : DSInt(lb=1, ub=6)})\n',
            'X_Y_Position': 'X_Y_Position = DSRecord({"x" : DSInt(lb=0, ub=10), "y" : DSInt(lb=0, ub=10)})\n'})
        self.assertEqual(intput_variable_spec[0], {
            'description': '',
            'initialization': 'BOX_HEIGHT : int = 6',
            'type': 'BOX_HEIGHT : int',
            'variable_dslcode_template': 'BOX_HEIGHT : int = {}',
            'variable_instance': [6],
            'variable_name': 'BOX_HEIGHT'})
        self.assertEqual(intput_variable_spec[1]["variable_name"], 'BOX_WIDTH')
        self.assertEqual(intput_variable_spec[1]["variable_dslcode_template"], 'BOX_WIDTH : int = {}')
        self.assertEqual(intput_variable_spec[2], {
            'description': '',
            'initialization': 'ITEMS : Annotated[list[Item], Len(5, 5)] = [{\'width\': 4, \'height\': 3}, {\'width\': 1, \'height\': 2}, {\'width\': 5, \'height\': 3}, {\'width\': 4, \'height\': 2}, {\'width\': 1, \'height\': 3}]\nN_ITEMS : int = 5',
            'type': 'ITEMS : DSList(length = {}, elem_type = Item)',
            'variable_dslcode_template': 'ITEMS : DSList(length = {}, elem_type = Item) = {}\nN_ITEMS : int = {}',
            'variable_instance': [5, [{'height': 3, 'width': 4}, {'height': 2, 'width': 1}, {'height': 3, 'width': 5}, {'height': 2, 'width': 4}, {'height': 3, 'width': 1}], 5],
            'variable_name': 'ITEMS'})
        self.assertEqual(output_variable_spec[0]["variable_name"], "nr_used_boxes")
        self.assertEqual(output_variable_spec[0]["variable_dslcode_template"], 'nr_used_boxes : DSInt(lb={}, ub={})')
        self.assertEqual(output_variable_spec[1]["variable_name"], 'item_box_assignments')
        self.assertEqual(output_variable_spec[1]["variable_dslcode_template"],
                         'item_box_assignments : DSList(length = {}, elem_type = DSInt(lb={}, ub={}))\nN_ITEM_BOX_ASSIGNMENTS : int = {}')
        self.assertEqual(output_variable_spec[2]["variable_name"], 'x_y_positions')
        self.assertEqual(output_variable_spec[2]["variable_dslcode_template"],
                         'x_y_positions : DSList(length = {}, elem_type = X_Y_Position)\nN_X_Y_POSITIONS : int = {}')

    def test_reuse_model_fixed_inoutput_values(self):
        updated_models_filename = TreeBase.use_given_model_with_input("models/optDSL_resusable_models_test.json",
                                            "problem_descriptions/2d_bin_packing_generic_input_and_output_inst_2.json")
        with open(updated_models_filename, "r", encoding="utf-8") as f:
            updated_models = json.load(f)
        with open("models/optDSL_resusable_models_test_solution.json", "r", encoding="utf-8") as f:
            updated_models_solution = json.load(f)
        self.assertEqual(updated_models[0]["problem_description"], updated_models_solution[0]["problem_description"])
        self.assertEqual(updated_models[0]["llm_generated_objects"], updated_models_solution[0]["llm_generated_objects"])
        self.assertEqual(updated_models[0]["script_generated_objects"], updated_models_solution[0]["script_generated_objects"])
        self.assertEqual(updated_models[0]["constants"], updated_models_solution[0]["constants"])
        self.assertEqual(updated_models[0]["decision_variables"], updated_models_solution[0]["decision_variables"])
        self.assertEqual(updated_models[0]["objective"], updated_models_solution[0]["objective"])
        self.assertEqual(updated_models[0]["constraints"], updated_models_solution[0]["constraints"])
        self.assertEqual(updated_models[0]["full_formulation"], updated_models_solution[0]["full_formulation"])
        os.remove(updated_models_filename)


if __name__ == "__main__":
    unittest.main()
