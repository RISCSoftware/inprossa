import json
import subprocess

import re
import ast
from typing import Any, Dict
from minizinc import Model, Solver, Instance


class MiniZincSolver():
    def solve_with_command_line_minizinc(self, minizinc_code: str):
        # write the MiniZinc model to temp.mzn
        with open("temp.mzn", "w", encoding="utf-8") as f:
            f.write(minizinc_code)

        # run minizinc on the file
        result = subprocess.run(
            ["minizinc", "--solver", "gecode", "--no-intermediate", "--output-mode", "item", "temp.mzn"],
            capture_output=True,
            text=True
        )

        # you can inspect returncode, stdout, stderr
        print("Return code:", result.returncode)
        if result.stdout:
            if "unknown" not in result.stdout.lower() and "unsatisfiable" not in result.stdout.lower():
                filtered_result = ""
                for line in result.stdout.splitlines():
                    if "===" in line or "---" in line:
                        continue
                    filtered_result += line
                parsed = self.minizinc_item_to_dict(filtered_result)
                parsed_solution = json.dumps(parsed, indent=4)
                print("Output:\n", parsed_solution)
                return parsed_solution
            else:
                print("Output:\n", result.stdout)
        if result.stderr:
            print("Errors:\\n", result.stderr)
        return None


    def solve_with_python_minizinc(self, minizinc_code: str):
        minizinc_code = """
        type Item = record(
            1..10: width,
            1..6: height
        );
        type BoxAssignment = record(
            1..6: box_id,
            0..10: x,
            0..6: y
        );
        type Position = record(
            0..10: x,
            0..6: y
        );
        int: BOX_HEIGHT = 6;
        int: BOX_WIDTH = 10;
        Item: ITEM1 = (width: 4, height: 3);
        Item: ITEM2 = (width: 3, height: 2);
        Item: ITEM3 = (width: 5, height: 3);
        Item: ITEM4 = (width: 2, height: 4);
        Item: ITEM5 = (width: 3, height: 3);
        Item: ITEM6 = (width: 5, height: 2);
        int: N_ITEMS = 6;
        array[1..6] of Item: ITEMS = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6];
        array[1..1] of var int: objective;
        array[1..1] of var 1..6: nr_used_boxes;
        array[1..1, 1..6] of record( % ATTENTION: array[1..1, 1..6] VS array[1..1] of array[1..6]
            var 1..6: box_id,
            var 0..10: x,
            var 0..6: y
        ): item_box_assignment;
        % ATTENTION: array access different too: item_box_assignment[1][1].x to item_box_assignment[1,1].x
        % ATTENTION: for first row and all columns, write item_box_assignment[1, ..] not item_box_assignment[1]
        constraint objective[1] = 0;
        solve minimize objective[1];"""
        # Corrected complete optimal example
        minizinc_code = """type Item = record(
    1..10: width,
    1..6: height
);
type BoxAssignment = record(
    1..6: box_id,
    0..10: x,
    0..6: y
);
type Position = record(
    0..10: x,
    0..6: y
);
predicate assign_item_positions(array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): input_1, array[1..6] of record(
    var 0..10: x,
    var 0..6: y
): input_2, array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment, array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments, array[1..1] of var int: objective, array[1..6] of record(
    var 0..10: x,
    var 0..6: y
): position, array[1..1, 1..6] of record(
    var 0..10: x,
    var 0..6: y
): positions) =
    (
    assignments[1,1].box_id = input_1[1].box_id /\\
    assignments[1,1].x = input_1[1].x /\\
    assignments[1,1].y = input_1[1].y /\\
    assignments[1,2].box_id = input_1[2].box_id /\\
    assignments[1,2].x = input_1[2].x /\\
    assignments[1,2].y = input_1[2].y /\\
    assignments[1,3].box_id = input_1[3].box_id /\\
    assignments[1,3].x = input_1[3].x /\\
    assignments[1,3].y = input_1[3].y /\\
    assignments[1,4].box_id = input_1[4].box_id /\\
    assignments[1,4].x = input_1[4].x /\\
    assignments[1,4].y = input_1[4].y /\\
    assignments[1,5].box_id = input_1[5].box_id /\\
    assignments[1,5].x = input_1[5].x /\\
    assignments[1,5].y = input_1[5].y /\\
    assignments[1,6].box_id = input_1[6].box_id /\\
    assignments[1,6].x = input_1[6].x /\\
    assignments[1,6].y = input_1[6].y /\\
    positions[1,1].x = input_2[1].x /\\
    positions[1,1].y = input_2[1].y /\\
    positions[1,2].x = input_2[2].x /\\
    positions[1,2].y = input_2[2].y /\\
    positions[1,3].x = input_2[3].x /\\
    positions[1,3].y = input_2[3].y /\\
    positions[1,4].x = input_2[4].x /\\
    positions[1,4].y = input_2[4].y /\\
    positions[1,5].x = input_2[5].x /\\
    positions[1,5].y = input_2[5].y /\\
    positions[1,6].x = input_2[6].x /\\
    positions[1,6].y = input_2[6].y /\\
    objective[1] = 0 /\\
    assignment[1].box_id = assignments[1,1].box_id /\\
    assignment[1].x = assignments[1,1].x /\\
    assignment[1].y = assignments[1,1].y /\\
    position[1].x = positions[1,1].x /\\
    position[1].y = positions[1,1].y /\\
    (position[1].x = assignment[1].x) /\\
    (position[1].y = assignment[1].y) /\\
    assignment[2].box_id = assignments[1,2].box_id /\\
    assignment[2].x = assignments[1,2].x /\\
    assignment[2].y = assignments[1,2].y /\\
    position[2].x = positions[1,2].x /\\
    position[2].y = positions[1,2].y /\\
    (position[2].x = assignment[2].x) /\\
    (position[2].y = assignment[2].y) /\\
    assignment[3].box_id = assignments[1,3].box_id /\\
    assignment[3].x = assignments[1,3].x /\\
    assignment[3].y = assignments[1,3].y /\\
    position[3].x = positions[1,3].x /\\
    position[3].y = positions[1,3].y /\\
    (position[3].x = assignment[3].x) /\\
    (position[3].y = assignment[3].y) /\\
    assignment[4].box_id = assignments[1,4].box_id /\\
    assignment[4].x = assignments[1,4].x /\\
    assignment[4].y = assignments[1,4].y /\\
    position[4].x = positions[1,4].x /\\
    position[4].y = positions[1,4].y /\\
    (position[4].x = assignment[4].x) /\\
    (position[4].y = assignment[4].y) /\\
    assignment[5].box_id = assignments[1,5].box_id /\\
    assignment[5].x = assignments[1,5].x /\\
    assignment[5].y = assignments[1,5].y /\\
    position[5].x = positions[1,5].x /\\
    position[5].y = positions[1,5].y /\\
    (position[5].x = assignment[5].x) /\\
    (position[5].y = assignment[5].y) /\\
    assignment[6].box_id = assignments[1,6].box_id /\\
    assignment[6].x = assignments[1,6].x /\\
    assignment[6].y = assignments[1,6].y /\\
    position[6].x = positions[1,6].x /\\
    position[6].y = positions[1,6].y /\\
    (position[6].x = assignment[6].x) /\\
    (position[6].y = assignment[6].y)
    );
predicate calculate_objective(array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): input_1, var 1..6: output_1, array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments, array[1..6] of var 1..6: box_id, array[1..7] of var 1..6: max_box_id, array[1..1] of var int: objective) =
    (
    assignments[1,1].box_id = input_1[1].box_id /\\
    assignments[1,1].x = input_1[1].x /\\
    assignments[1,1].y = input_1[1].y /\\
    assignments[1,2].box_id = input_1[2].box_id /\\
    assignments[1,2].x = input_1[2].x /\\
    assignments[1,2].y = input_1[2].y /\\
    assignments[1,3].box_id = input_1[3].box_id /\\
    assignments[1,3].x = input_1[3].x /\\
    assignments[1,3].y = input_1[3].y /\\
    assignments[1,4].box_id = input_1[4].box_id /\\
    assignments[1,4].x = input_1[4].x /\\
    assignments[1,4].y = input_1[4].y /\\
    assignments[1,5].box_id = input_1[5].box_id /\\
    assignments[1,5].x = input_1[5].x /\\
    assignments[1,5].y = input_1[5].y /\\
    assignments[1,6].box_id = input_1[6].box_id /\\
    assignments[1,6].x = input_1[6].x /\\
    assignments[1,6].y = input_1[6].y /\\
    objective[1] = 0 /\\
    max_box_id[1] = 1 /\\
    box_id[1] = assignments[1,1].box_id /\\
    ((box_id[1] > max_box_id[1]) -> max_box_id[2] = box_id[1]) /\\
    ((not (box_id[1] > max_box_id[1])) -> max_box_id[2] = max_box_id[1]) /\\
    box_id[2] = assignments[1,2].box_id /\\
    ((box_id[2] > max_box_id[2]) -> max_box_id[3] = box_id[2]) /\\
    ((not (box_id[2] > max_box_id[2])) -> max_box_id[3] = max_box_id[2]) /\\
    box_id[3] = assignments[1,3].box_id /\\
    ((box_id[3] > max_box_id[3]) -> max_box_id[4] = box_id[3]) /\\
    ((not (box_id[3] > max_box_id[3])) -> max_box_id[4] = max_box_id[3]) /\\
    box_id[4] = assignments[1,4].box_id /\\
    ((box_id[4] > max_box_id[4]) -> max_box_id[5] = box_id[4]) /\\
    ((not (box_id[4] > max_box_id[4])) -> max_box_id[5] = max_box_id[4]) /\\
    box_id[5] = assignments[1,5].box_id /\\
    ((box_id[5] > max_box_id[5]) -> max_box_id[6] = box_id[5]) /\\
    ((not (box_id[5] > max_box_id[5])) -> max_box_id[6] = max_box_id[5]) /\\
    box_id[6] = assignments[1,6].box_id /\\
    ((box_id[6] > max_box_id[6]) -> max_box_id[7] = box_id[6]) /\\
    ((not (box_id[6] > max_box_id[6])) -> max_box_id[7] = max_box_id[6]) /\\
    output_1 = max_box_id[7]
    );
predicate items_fit_exactly_in_boxes(array[1..6] of record(
    var 1..10: width,
    var 1..6: height
): input_1, array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): input_2, array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment, array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments, array[1..6] of record(
    var 1..10: width,
    var 1..6: height
): item, array[1..1, 1..6] of record(
    var 1..10: width,
    var 1..6: height
): items, array[1..1] of var int: objective) =
    (
    items[1,1].width = input_1[1].width /\\
    items[1,1].height = input_1[1].height /\\
    items[1,2].width = input_1[2].width /\\
    items[1,2].height = input_1[2].height /\\
    items[1,3].width = input_1[3].width /\\
    items[1,3].height = input_1[3].height /\\
    items[1,4].width = input_1[4].width /\\
    items[1,4].height = input_1[4].height /\\
    items[1,5].width = input_1[5].width /\\
    items[1,5].height = input_1[5].height /\\
    items[1,6].width = input_1[6].width /\\
    items[1,6].height = input_1[6].height /\\
    assignments[1,1].box_id = input_2[1].box_id /\\
    assignments[1,1].x = input_2[1].x /\\
    assignments[1,1].y = input_2[1].y /\\
    assignments[1,2].box_id = input_2[2].box_id /\\
    assignments[1,2].x = input_2[2].x /\\
    assignments[1,2].y = input_2[2].y /\\
    assignments[1,3].box_id = input_2[3].box_id /\\
    assignments[1,3].x = input_2[3].x /\\
    assignments[1,3].y = input_2[3].y /\\
    assignments[1,4].box_id = input_2[4].box_id /\\
    assignments[1,4].x = input_2[4].x /\\
    assignments[1,4].y = input_2[4].y /\\
    assignments[1,5].box_id = input_2[5].box_id /\\
    assignments[1,5].x = input_2[5].x /\\
    assignments[1,5].y = input_2[5].y /\\
    assignments[1,6].box_id = input_2[6].box_id /\\
    assignments[1,6].x = input_2[6].x /\\
    assignments[1,6].y = input_2[6].y /\\
    objective[1] = 0 /\\
    item[1].width = items[1,1].width /\\
    item[1].height = items[1,1].height /\\
    assignment[1].box_id = assignments[1,1].box_id /\\
    assignment[1].x = assignments[1,1].x /\\
    assignment[1].y = assignments[1,1].y /\\
    ((assignment[1].x + item[1].width) <= BOX_WIDTH) /\\
    ((assignment[1].y + item[1].height) <= BOX_HEIGHT) /\\
    item[2].width = items[1,2].width /\\
    item[2].height = items[1,2].height /\\
    assignment[2].box_id = assignments[1,2].box_id /\\
    assignment[2].x = assignments[1,2].x /\\
    assignment[2].y = assignments[1,2].y /\\
    ((assignment[2].x + item[2].width) <= BOX_WIDTH) /\\
    ((assignment[2].y + item[2].height) <= BOX_HEIGHT) /\\
    item[3].width = items[1,3].width /\\
    item[3].height = items[1,3].height /\\
    assignment[3].box_id = assignments[1,3].box_id /\\
    assignment[3].x = assignments[1,3].x /\\
    assignment[3].y = assignments[1,3].y /\\
    ((assignment[3].x + item[3].width) <= BOX_WIDTH) /\\
    ((assignment[3].y + item[3].height) <= BOX_HEIGHT) /\\
    item[4].width = items[1,4].width /\\
    item[4].height = items[1,4].height /\\
    assignment[4].box_id = assignments[1,4].box_id /\\
    assignment[4].x = assignments[1,4].x /\\
    assignment[4].y = assignments[1,4].y /\\
    ((assignment[4].x + item[4].width) <= BOX_WIDTH) /\\
    ((assignment[4].y + item[4].height) <= BOX_HEIGHT) /\\
    item[5].width = items[1,5].width /\\
    item[5].height = items[1,5].height /\\
    assignment[5].box_id = assignments[1,5].box_id /\\
    assignment[5].x = assignments[1,5].x /\\
    assignment[5].y = assignments[1,5].y /\\
    ((assignment[5].x + item[5].width) <= BOX_WIDTH) /\\
    ((assignment[5].y + item[5].height) <= BOX_HEIGHT) /\\
    item[6].width = items[1,6].width /\\
    item[6].height = items[1,6].height /\\
    assignment[6].box_id = assignments[1,6].box_id /\\
    assignment[6].x = assignments[1,6].x /\\
    assignment[6].y = assignments[1,6].y /\\
    ((assignment[6].x + item[6].width) <= BOX_WIDTH) /\\
    ((assignment[6].y + item[6].height) <= BOX_HEIGHT)
    );
predicate no_overlap(array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): input_1, array[1..6] of record(
    var 1..10: width,
    var 1..6: height
): input_2, array[1..15] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment_i, array[1..15] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment_j, array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments, array[1..15] of record(
    var 1..10: width,
    var 1..6: height
): item_i, array[1..15] of record(
    var 1..10: width,
    var 1..6: height
): item_j, array[1..1, 1..6] of record(
    var 1..10: width,
    var 1..6: height
): items, array[1..15] of var bool: no_overlap_x, array[1..15] of var bool: no_overlap_y, array[1..1] of var int: objective, array[1..15] of var bool: same_box) =
    (
    assignments[1,1].box_id = input_1[1].box_id /\\
    assignments[1,1].x = input_1[1].x /\\
    assignments[1,1].y = input_1[1].y /\\
    assignments[1,2].box_id = input_1[2].box_id /\\
    assignments[1,2].x = input_1[2].x /\\
    assignments[1,2].y = input_1[2].y /\\
    assignments[1,3].box_id = input_1[3].box_id /\\
    assignments[1,3].x = input_1[3].x /\\
    assignments[1,3].y = input_1[3].y /\\
    assignments[1,4].box_id = input_1[4].box_id /\\
    assignments[1,4].x = input_1[4].x /\\
    assignments[1,4].y = input_1[4].y /\\
    assignments[1,5].box_id = input_1[5].box_id /\\
    assignments[1,5].x = input_1[5].x /\\
    assignments[1,5].y = input_1[5].y /\\
    assignments[1,6].box_id = input_1[6].box_id /\\
    assignments[1,6].x = input_1[6].x /\\
    assignments[1,6].y = input_1[6].y /\\
    items[1,1].width = input_2[1].width /\\
    items[1,1].height = input_2[1].height /\\
    items[1,2].width = input_2[2].width /\\
    items[1,2].height = input_2[2].height /\\
    items[1,3].width = input_2[3].width /\\
    items[1,3].height = input_2[3].height /\\
    items[1,4].width = input_2[4].width /\\
    items[1,4].height = input_2[4].height /\\
    items[1,5].width = input_2[5].width /\\
    items[1,5].height = input_2[5].height /\\
    items[1,6].width = input_2[6].width /\\
    items[1,6].height = input_2[6].height /\\
    objective[1] = 0 /\\
    assignment_i[1].box_id = assignments[1,1].box_id /\\
    assignment_i[1].x = assignments[1,1].x /\\
    assignment_i[1].y = assignments[1,1].y /\\
    assignment_j[1].box_id = assignments[1,2].box_id /\\
    assignment_j[1].x = assignments[1,2].x /\\
    assignment_j[1].y = assignments[1,2].y /\\
    item_i[1].width = items[1,1].width /\\
    item_i[1].height = items[1,1].height /\\
    item_j[1].width = items[1,2].width /\\
    item_j[1].height = items[1,2].height /\\
    same_box[1] = (assignment_i[1].box_id = assignment_j[1].box_id) /\\
    no_overlap_x[1] = (((assignment_i[1].x + item_i[1].width) <= assignment_j[1].x) \\/ ((assignment_j[1].x + item_j[1].width) <= assignment_i[1].x)) /\\
    no_overlap_y[1] = (((assignment_i[1].y + item_i[1].height) <= assignment_j[1].y) \\/ ((assignment_j[1].y + item_j[1].height) <= assignment_i[1].y)) /\\
    ((not same_box[1]) \\/ (no_overlap_x[1] \\/ no_overlap_y[1])) /\\
    assignment_i[2].box_id = assignments[1,1].box_id /\\
    assignment_i[2].x = assignments[1,1].x /\\
    assignment_i[2].y = assignments[1,1].y /\\
    assignment_j[2].box_id = assignments[1,3].box_id /\\
    assignment_j[2].x = assignments[1,3].x /\\
    assignment_j[2].y = assignments[1,3].y /\\
    item_i[2].width = items[1,1].width /\\
    item_i[2].height = items[1,1].height /\\
    item_j[2].width = items[1,3].width /\\
    item_j[2].height = items[1,3].height /\\
    same_box[2] = (assignment_i[2].box_id = assignment_j[2].box_id) /\\
    no_overlap_x[2] = (((assignment_i[2].x + item_i[2].width) <= assignment_j[2].x) \\/ ((assignment_j[2].x + item_j[2].width) <= assignment_i[2].x)) /\\
    no_overlap_y[2] = (((assignment_i[2].y + item_i[2].height) <= assignment_j[2].y) \\/ ((assignment_j[2].y + item_j[2].height) <= assignment_i[2].y)) /\\
    ((not same_box[2]) \\/ (no_overlap_x[2] \\/ no_overlap_y[2])) /\\
    assignment_i[3].box_id = assignments[1,1].box_id /\\
    assignment_i[3].x = assignments[1,1].x /\\
    assignment_i[3].y = assignments[1,1].y /\\
    assignment_j[3].box_id = assignments[1,4].box_id /\\
    assignment_j[3].x = assignments[1,4].x /\\
    assignment_j[3].y = assignments[1,4].y /\\
    item_i[3].width = items[1,1].width /\\
    item_i[3].height = items[1,1].height /\\
    item_j[3].width = items[1,4].width /\\
    item_j[3].height = items[1,4].height /\\
    same_box[3] = (assignment_i[3].box_id = assignment_j[3].box_id) /\\
    no_overlap_x[3] = (((assignment_i[3].x + item_i[3].width) <= assignment_j[3].x) \\/ ((assignment_j[3].x + item_j[3].width) <= assignment_i[3].x)) /\\
    no_overlap_y[3] = (((assignment_i[3].y + item_i[3].height) <= assignment_j[3].y) \\/ ((assignment_j[3].y + item_j[3].height) <= assignment_i[3].y)) /\\
    ((not same_box[3]) \\/ (no_overlap_x[3] \\/ no_overlap_y[3])) /\\
    assignment_i[4].box_id = assignments[1,1].box_id /\\
    assignment_i[4].x = assignments[1,1].x /\\
    assignment_i[4].y = assignments[1,1].y /\\
    assignment_j[4].box_id = assignments[1,5].box_id /\\
    assignment_j[4].x = assignments[1,5].x /\\
    assignment_j[4].y = assignments[1,5].y /\\
    item_i[4].width = items[1,1].width /\\
    item_i[4].height = items[1,1].height /\\
    item_j[4].width = items[1,5].width /\\
    item_j[4].height = items[1,5].height /\\
    same_box[4] = (assignment_i[4].box_id = assignment_j[4].box_id) /\\
    no_overlap_x[4] = (((assignment_i[4].x + item_i[4].width) <= assignment_j[4].x) \\/ ((assignment_j[4].x + item_j[4].width) <= assignment_i[4].x)) /\\
    no_overlap_y[4] = (((assignment_i[4].y + item_i[4].height) <= assignment_j[4].y) \\/ ((assignment_j[4].y + item_j[4].height) <= assignment_i[4].y)) /\\
    ((not same_box[4]) \\/ (no_overlap_x[4] \\/ no_overlap_y[4])) /\\
    assignment_i[5].box_id = assignments[1,1].box_id /\\
    assignment_i[5].x = assignments[1,1].x /\\
    assignment_i[5].y = assignments[1,1].y /\\
    assignment_j[5].box_id = assignments[1,6].box_id /\\
    assignment_j[5].x = assignments[1,6].x /\\
    assignment_j[5].y = assignments[1,6].y /\\
    item_i[5].width = items[1,1].width /\\
    item_i[5].height = items[1,1].height /\\
    item_j[5].width = items[1,6].width /\\
    item_j[5].height = items[1,6].height /\\
    same_box[5] = (assignment_i[5].box_id = assignment_j[5].box_id) /\\
    no_overlap_x[5] = (((assignment_i[5].x + item_i[5].width) <= assignment_j[5].x) \\/ ((assignment_j[5].x + item_j[5].width) <= assignment_i[5].x)) /\\
    no_overlap_y[5] = (((assignment_i[5].y + item_i[5].height) <= assignment_j[5].y) \\/ ((assignment_j[5].y + item_j[5].height) <= assignment_i[5].y)) /\\
    ((not same_box[5]) \\/ (no_overlap_x[5] \\/ no_overlap_y[5])) /\\
    assignment_i[6].box_id = assignments[1,2].box_id /\\
    assignment_i[6].x = assignments[1,2].x /\\
    assignment_i[6].y = assignments[1,2].y /\\
    assignment_j[6].box_id = assignments[1,3].box_id /\\
    assignment_j[6].x = assignments[1,3].x /\\
    assignment_j[6].y = assignments[1,3].y /\\
    item_i[6].width = items[1,2].width /\\
    item_i[6].height = items[1,2].height /\\
    item_j[6].width = items[1,3].width /\\
    item_j[6].height = items[1,3].height /\\
    same_box[6] = (assignment_i[6].box_id = assignment_j[6].box_id) /\\
    no_overlap_x[6] = (((assignment_i[6].x + item_i[6].width) <= assignment_j[6].x) \\/ ((assignment_j[6].x + item_j[6].width) <= assignment_i[6].x)) /\\
    no_overlap_y[6] = (((assignment_i[6].y + item_i[6].height) <= assignment_j[6].y) \\/ ((assignment_j[6].y + item_j[6].height) <= assignment_i[6].y)) /\\
    ((not same_box[6]) \\/ (no_overlap_x[6] \\/ no_overlap_y[6])) /\\
    assignment_i[7].box_id = assignments[1,2].box_id /\\
    assignment_i[7].x = assignments[1,2].x /\\
    assignment_i[7].y = assignments[1,2].y /\\
    assignment_j[7].box_id = assignments[1,4].box_id /\\
    assignment_j[7].x = assignments[1,4].x /\\
    assignment_j[7].y = assignments[1,4].y /\\
    item_i[7].width = items[1,2].width /\\
    item_i[7].height = items[1,2].height /\\
    item_j[7].width = items[1,4].width /\\
    item_j[7].height = items[1,4].height /\\
    same_box[7] = (assignment_i[7].box_id = assignment_j[7].box_id) /\\
    no_overlap_x[7] = (((assignment_i[7].x + item_i[7].width) <= assignment_j[7].x) \\/ ((assignment_j[7].x + item_j[7].width) <= assignment_i[7].x)) /\\
    no_overlap_y[7] = (((assignment_i[7].y + item_i[7].height) <= assignment_j[7].y) \\/ ((assignment_j[7].y + item_j[7].height) <= assignment_i[7].y)) /\\
    ((not same_box[7]) \\/ (no_overlap_x[7] \\/ no_overlap_y[7])) /\\
    assignment_i[8].box_id = assignments[1,2].box_id /\\
    assignment_i[8].x = assignments[1,2].x /\\
    assignment_i[8].y = assignments[1,2].y /\\
    assignment_j[8].box_id = assignments[1,5].box_id /\\
    assignment_j[8].x = assignments[1,5].x /\\
    assignment_j[8].y = assignments[1,5].y /\\
    item_i[8].width = items[1,2].width /\\
    item_i[8].height = items[1,2].height /\\
    item_j[8].width = items[1,5].width /\\
    item_j[8].height = items[1,5].height /\\
    same_box[8] = (assignment_i[8].box_id = assignment_j[8].box_id) /\\
    no_overlap_x[8] = (((assignment_i[8].x + item_i[8].width) <= assignment_j[8].x) \\/ ((assignment_j[8].x + item_j[8].width) <= assignment_i[8].x)) /\\
    no_overlap_y[8] = (((assignment_i[8].y + item_i[8].height) <= assignment_j[8].y) \\/ ((assignment_j[8].y + item_j[8].height) <= assignment_i[8].y)) /\\
    ((not same_box[8]) \\/ (no_overlap_x[8] \\/ no_overlap_y[8])) /\\
    assignment_i[9].box_id = assignments[1,2].box_id /\\
    assignment_i[9].x = assignments[1,2].x /\\
    assignment_i[9].y = assignments[1,2].y /\\
    assignment_j[9].box_id = assignments[1,6].box_id /\\
    assignment_j[9].x = assignments[1,6].x /\\
    assignment_j[9].y = assignments[1,6].y /\\
    item_i[9].width = items[1,2].width /\\
    item_i[9].height = items[1,2].height /\\
    item_j[9].width = items[1,6].width /\\
    item_j[9].height = items[1,6].height /\\
    same_box[9] = (assignment_i[9].box_id = assignment_j[9].box_id) /\\
    no_overlap_x[9] = (((assignment_i[9].x + item_i[9].width) <= assignment_j[9].x) \\/ ((assignment_j[9].x + item_j[9].width) <= assignment_i[9].x)) /\\
    no_overlap_y[9] = (((assignment_i[9].y + item_i[9].height) <= assignment_j[9].y) \\/ ((assignment_j[9].y + item_j[9].height) <= assignment_i[9].y)) /\\
    ((not same_box[9]) \\/ (no_overlap_x[9] \\/ no_overlap_y[9])) /\\
    assignment_i[10].box_id = assignments[1,3].box_id /\\
    assignment_i[10].x = assignments[1,3].x /\\
    assignment_i[10].y = assignments[1,3].y /\\
    assignment_j[10].box_id = assignments[1,4].box_id /\\
    assignment_j[10].x = assignments[1,4].x /\\
    assignment_j[10].y = assignments[1,4].y /\\
    item_i[10].width = items[1,3].width /\\
    item_i[10].height = items[1,3].height /\\
    item_j[10].width = items[1,4].width /\\
    item_j[10].height = items[1,4].height /\\
    same_box[10] = (assignment_i[10].box_id = assignment_j[10].box_id) /\\
    no_overlap_x[10] = (((assignment_i[10].x + item_i[10].width) <= assignment_j[10].x) \\/ ((assignment_j[10].x + item_j[10].width) <= assignment_i[10].x)) /\\
    no_overlap_y[10] = (((assignment_i[10].y + item_i[10].height) <= assignment_j[10].y) \\/ ((assignment_j[10].y + item_j[10].height) <= assignment_i[10].y)) /\\
    ((not same_box[10]) \\/ (no_overlap_x[10] \\/ no_overlap_y[10])) /\\
    assignment_i[11].box_id = assignments[1,3].box_id /\\
    assignment_i[11].x = assignments[1,3].x /\\
    assignment_i[11].y = assignments[1,3].y /\\
    assignment_j[11].box_id = assignments[1,5].box_id /\\
    assignment_j[11].x = assignments[1,5].x /\\
    assignment_j[11].y = assignments[1,5].y /\\
    item_i[11].width = items[1,3].width /\\
    item_i[11].height = items[1,3].height /\\
    item_j[11].width = items[1,5].width /\\
    item_j[11].height = items[1,5].height /\\
    same_box[11] = (assignment_i[11].box_id = assignment_j[11].box_id) /\\
    no_overlap_x[11] = (((assignment_i[11].x + item_i[11].width) <= assignment_j[11].x) \\/ ((assignment_j[11].x + item_j[11].width) <= assignment_i[11].x)) /\\
    no_overlap_y[11] = (((assignment_i[11].y + item_i[11].height) <= assignment_j[11].y) \\/ ((assignment_j[11].y + item_j[11].height) <= assignment_i[11].y)) /\\
    ((not same_box[11]) \\/ (no_overlap_x[11] \\/ no_overlap_y[11])) /\\
    assignment_i[12].box_id = assignments[1,3].box_id /\\
    assignment_i[12].x = assignments[1,3].x /\\
    assignment_i[12].y = assignments[1,3].y /\\
    assignment_j[12].box_id = assignments[1,6].box_id /\\
    assignment_j[12].x = assignments[1,6].x /\\
    assignment_j[12].y = assignments[1,6].y /\\
    item_i[12].width = items[1,3].width /\\
    item_i[12].height = items[1,3].height /\\
    item_j[12].width = items[1,6].width /\\
    item_j[12].height = items[1,6].height /\\
    same_box[12] = (assignment_i[12].box_id = assignment_j[12].box_id) /\\
    no_overlap_x[12] = (((assignment_i[12].x + item_i[12].width) <= assignment_j[12].x) \\/ ((assignment_j[12].x + item_j[12].width) <= assignment_i[12].x)) /\\
    no_overlap_y[12] = (((assignment_i[12].y + item_i[12].height) <= assignment_j[12].y) \\/ ((assignment_j[12].y + item_j[12].height) <= assignment_i[12].y)) /\\
    ((not same_box[12]) \\/ (no_overlap_x[12] \\/ no_overlap_y[12])) /\\
    assignment_i[13].box_id = assignments[1,4].box_id /\\
    assignment_i[13].x = assignments[1,4].x /\\
    assignment_i[13].y = assignments[1,4].y /\\
    assignment_j[13].box_id = assignments[1,5].box_id /\\
    assignment_j[13].x = assignments[1,5].x /\\
    assignment_j[13].y = assignments[1,5].y /\\
    item_i[13].width = items[1,4].width /\\
    item_i[13].height = items[1,4].height /\\
    item_j[13].width = items[1,5].width /\\
    item_j[13].height = items[1,5].height /\\
    same_box[13] = (assignment_i[13].box_id = assignment_j[13].box_id) /\\
    no_overlap_x[13] = (((assignment_i[13].x + item_i[13].width) <= assignment_j[13].x) \\/ ((assignment_j[13].x + item_j[13].width) <= assignment_i[13].x)) /\\
    no_overlap_y[13] = (((assignment_i[13].y + item_i[13].height) <= assignment_j[13].y) \\/ ((assignment_j[13].y + item_j[13].height) <= assignment_i[13].y)) /\\
    ((not same_box[13]) \\/ (no_overlap_x[13] \\/ no_overlap_y[13])) /\\
    assignment_i[14].box_id = assignments[1,4].box_id /\\
    assignment_i[14].x = assignments[1,4].x /\\
    assignment_i[14].y = assignments[1,4].y /\\
    assignment_j[14].box_id = assignments[1,6].box_id /\\
    assignment_j[14].x = assignments[1,6].x /\\
    assignment_j[14].y = assignments[1,6].y /\\
    item_i[14].width = items[1,4].width /\\
    item_i[14].height = items[1,4].height /\\
    item_j[14].width = items[1,6].width /\\
    item_j[14].height = items[1,6].height /\\
    same_box[14] = (assignment_i[14].box_id = assignment_j[14].box_id) /\\
    no_overlap_x[14] = (((assignment_i[14].x + item_i[14].width) <= assignment_j[14].x) \\/ ((assignment_j[14].x + item_j[14].width) <= assignment_i[14].x)) /\\
    no_overlap_y[14] = (((assignment_i[14].y + item_i[14].height) <= assignment_j[14].y) \\/ ((assignment_j[14].y + item_j[14].height) <= assignment_i[14].y)) /\\
    ((not same_box[14]) \\/ (no_overlap_x[14] \\/ no_overlap_y[14])) /\\
    assignment_i[15].box_id = assignments[1,5].box_id /\\
    assignment_i[15].x = assignments[1,5].x /\\
    assignment_i[15].y = assignments[1,5].y /\\
    assignment_j[15].box_id = assignments[1,6].box_id /\\
    assignment_j[15].x = assignments[1,6].x /\\
    assignment_j[15].y = assignments[1,6].y /\\
    item_i[15].width = items[1,5].width /\\
    item_i[15].height = items[1,5].height /\\
    item_j[15].width = items[1,6].width /\\
    item_j[15].height = items[1,6].height /\\
    same_box[15] = (assignment_i[15].box_id = assignment_j[15].box_id) /\\
    no_overlap_x[15] = (((assignment_i[15].x + item_i[15].width) <= assignment_j[15].x) \\/ ((assignment_j[15].x + item_j[15].width) <= assignment_i[15].x)) /\\
    no_overlap_y[15] = (((assignment_i[15].y + item_i[15].height) <= assignment_j[15].y) \\/ ((assignment_j[15].y + item_j[15].height) <= assignment_i[15].y)) /\\
    ((not same_box[15]) \\/ (no_overlap_x[15] \\/ no_overlap_y[15]))
    );
int: BOX_HEIGHT = 6;
int: BOX_WIDTH = 10;
Item: ITEM1 = (width: 4, height: 3);
Item: ITEM2 = (width: 3, height: 2);
Item: ITEM3 = (width: 5, height: 3);
Item: ITEM4 = (width: 2, height: 4);
Item: ITEM5 = (width: 3, height: 3);
Item: ITEM6 = (width: 5, height: 2);
array[1..6] of Item: ITEMS = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6];
int: N_ITEMS = 6;
array[1..6] of var int: objective;
array[1..1] of var 1..6: nr_used_boxes;
array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): item_box_assignment;
array[1..1, 1..6] of record(
    var 0..10: x,
    var 0..6: y
): x_y_positions;
array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments__calculate_objective__1;
array[1..6] of var 1..6: box_id__calculate_objective__1;
array[1..7] of var 1..6: max_box_id__calculate_objective__1;
array[1..1] of var int: objective__calculate_objective__1;
array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment__items_fit_exactly_in_boxes__1;
array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments__items_fit_exactly_in_boxes__1;
array[1..6] of record(
    var 1..10: width,
    var 1..6: height
): item__items_fit_exactly_in_boxes__1;
array[1..1, 1..6] of record(
    var 1..10: width,
    var 1..6: height
): items__items_fit_exactly_in_boxes__1;
array[1..1] of var int: objective__items_fit_exactly_in_boxes__1;
array[1..15] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment_i__no_overlap__1;
array[1..15] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment_j__no_overlap__1;
array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments__no_overlap__1;
array[1..15] of record(
    var 1..10: width,
    var 1..6: height
): item_i__no_overlap__1;
array[1..15] of record(
    var 1..10: width,
    var 1..6: height
): item_j__no_overlap__1;
array[1..1, 1..6] of record(
    var 1..10: width,
    var 1..6: height
): items__no_overlap__1;
array[1..15] of var bool: no_overlap_x__no_overlap__1;
array[1..15] of var bool: no_overlap_y__no_overlap__1;
array[1..1] of var int: objective__no_overlap__1;
array[1..15] of var bool: same_box__no_overlap__1;
array[1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignment__assign_item_positions__1;
array[1..1, 1..6] of record(
    var 1..6: box_id,
    var 0..10: x,
    var 0..6: y
): assignments__assign_item_positions__1;
array[1..1] of var int: objective__assign_item_positions__1;
array[1..6] of record(
    var 0..10: x,
    var 0..6: y
): position__assign_item_positions__1;
array[1..1, 1..6] of record(
    var 0..10: x,
    var 0..6: y
): positions__assign_item_positions__1;
constraint objective[1] = 0;
constraint calculate_objective(item_box_assignment[1, ..], nr_used_boxes[1], assignments__calculate_objective__1, box_id__calculate_objective__1, max_box_id__calculate_objective__1, objective__calculate_objective__1);
constraint objective[2] = (objective[1] + objective__calculate_objective__1[1]);
constraint objective[3] = nr_used_boxes[1];
constraint items_fit_exactly_in_boxes(ITEMS, item_box_assignment[1, ..], assignment__items_fit_exactly_in_boxes__1, assignments__items_fit_exactly_in_boxes__1, item__items_fit_exactly_in_boxes__1, items__items_fit_exactly_in_boxes__1, objective__items_fit_exactly_in_boxes__1);
constraint objective[4] = (objective[3] + objective__items_fit_exactly_in_boxes__1[1]);
constraint no_overlap(item_box_assignment[1, ..], ITEMS, assignment_i__no_overlap__1, assignment_j__no_overlap__1, assignments__no_overlap__1, item_i__no_overlap__1, item_j__no_overlap__1, items__no_overlap__1, no_overlap_x__no_overlap__1, no_overlap_y__no_overlap__1, objective__no_overlap__1, same_box__no_overlap__1);
constraint objective[5] = (objective[4] + objective__no_overlap__1[1]);
constraint assign_item_positions(item_box_assignment[1, ..], x_y_positions[1, ..], assignment__assign_item_positions__1, assignments__assign_item_positions__1, objective__assign_item_positions__1, position__assign_item_positions__1, positions__assign_item_positions__1);
constraint objective[6] = (objective[5] + objective__assign_item_positions__1[1]);
solve minimize objective[6];"""

        # 1. Create a MiniZinc model
        #model = Model("temp.mzn")
        model = Model()
        model.add_string(minizinc_code)

        # 2. Choose a solver
        gecode = Solver.lookup("gecode")

        # 3. Bind model to solver to create an instance
        inst = Instance(gecode, model)

        # 4. Solve
        result = inst.solve()

        # 5. Inspect result
        print(result)


    # def solve_with_pymnz(self, minizinc_code: str):
    '''
    def solve_with_pymnz(self, minizinc_code: str):
        solns = pymzn.minizinc(minizinc_code, output_mode="item")
        parsed = self.minizinc_item_to_dict(solns[0])
        parsed_solution = json.dumps(parsed, indent=4)
        print(parsed_solution)
    '''


    def minizinc_item_to_dict(self, s: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        parts = [p.strip() for p in s.split(';') if p.strip()]
        for part in parts:
            if '=' not in part:
                continue
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip()

            # Convert record syntax: (field: v, ...) → { "field": v, ...}
            py = val.replace('(', '{').replace(')', '}')
            py = re.sub(r'([A-Za-z_]\w*)\s*:', r'"\1":', py)

            # Convert MiniZinc boolean literals to Python booleans
            py = (re.compile(r'\b(true|false)\b', flags=re.IGNORECASE)
                  .sub(lambda m: m.group(1).lower().capitalize(), py))

            try:
                parsed = ast.literal_eval(py)
            except Exception as e:
                raise ValueError(f"Cannot parse value for {key!r}.\nTransformed: {py!r}\nError: {e}")
            result[key] = parsed
        return result
