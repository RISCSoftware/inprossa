import unittest

class AddTests(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)

    def extract_assignment_and_position(self, solution: dict, variable_names: list[str]):
        solution = []
        box_assigments = solution["item_box_assignment"]
        for box_assigment in range(len(box_assigments)):
            if isinstance(box_assigment, int):
                solution.append({})
        for i, box_assigment in enumerate(box_assigments):
            if isinstance(box_assigment, int):
                solution[i].update({"box_id": box_assigment})
            elif isinstance(box_assigment, dict):
                for key in box_assigment.keys():
                    if "box" in key:
                        solution[i].update({"box_id": box_assigment[key]})
                    elif "item" in key:
                        solution[i].update({"item_id": box_assigment[key]})
                    elif "x" in key:
                        solution[i].update({"x": box_assigment[key]})
                    elif "y" in key:
                        solution[i].update({"y": box_assigment[key]})
                    else:
                        self.fail("Unreadable format of x_y_positions of x,y from solver solution for validation.")
            else:
                self.fail(f"Unreadable format of item_box_assignment of solver solution for validation.")
        if "x" not in solution[0]:
            positions = solution["x_y_positions"]
            if isinstance(positions, dict):
                for i, key in enumerate(positions.keys()):
                    if "x" in key:
                        solution[i].update({"x": positions[key]})
                    elif "y" in key:
                        solution[i].update({"y": positions[key]})
                    else:
                        self.fail("Unreadable format of x_y_positions of x,y from solver solution for validation.")
            else:
                self.fail("Unreadable format of x_y_positions of solver solution for validation.")

    def validate_solution(self, solution_and_task: dict):
        solution, task = solution_and_task
        objective_val = solution["_objective"]
        # extract assigments to an array of dicts: box_id, x, y
        solution = self.extract_assignment_and_position(solution, [variable_def["mandatory_variable_name"] for variable_def in task])
        given_items = task["input"]["ITEMS"]
        box_height = len(task["input"]["BOX_HEIGHT"])
        box_width = len(task["input"]["BOX_WIDTH"])
        if len(solution) != len(given_items):
            self.fail("Incorrect number of items.")

        for i, item_placement in enumerate(solution):
            if "item_id" in item_placement:
                item = item_placement["item_id"]
            else:
                item = given_items[i]

            self.assertLessEqual(item_placement.x + item.width, box_width)
            self.assertLessEqual(item_placement.y + item.height, box_height)
            self.assertGreaterEqual(item_placement.box_id, 0)
            self.assertLessEqual(item_placement.box_id, 6)
            for j in range(i + 1, len(solution)):
                item_i = given_items[i]
                item_j = given_items[j]
                assign_i = item_placement
                assign_j = solution[j]

                # Check if items are in the same box
                if assign_i["box_id"] == assign_j["box_id"]:

                    # Check for non-overlapping in x-axis
                    self.assertGreater(assign_i["x"] + item_i["width"], assign_j["x"])
                    self.assertGreater(assign_j["x"] + item_j["width"], assign_i["x"])

                    # Check for non-overlapping in y-axis
                    self.assertGreater(assign_i["y"] + item_i["height"], assign_j["y"])
                    self.assertGreater(assign_j["y"] + item_j["height"], assign_i["y"])


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(AddTests)
    result = unittest.TextTestRunner().run(suite)
    return result.wasSuccessful()

# Example of calling from another function:
if __name__ == "__main__":
    success = run_tests()
    print("Tests passed?" , success)