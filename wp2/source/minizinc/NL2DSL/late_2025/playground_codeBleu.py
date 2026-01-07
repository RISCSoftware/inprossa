from codebleu import calc_codebleu

print("prediction vs reference")
prediction = """def ensure_item_in_one_box(assignment: DSList(length=6, elem_type=BoxAssignment)):
    for i in range(1, 7):
        box_id = assignment[i].box_id
        assert box_id >= 1"""
reference = """def ensure_item_in_one_box(assignments: DSList(length=6, elem_type=BoxAssignment)):
    for i in range(1, 7):
        assert assignments[i].box_id >= 1"""
result = calc_codebleu([reference], [prediction], lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)
print(result)

print("\nswitch: prediction vs reference")
prediction = """def ensure_item_in_one_box(assignment: DSList(length=6, elem_type=BoxAssignment)):
    for i in range(1, 7):
        box_id = assignment[i].box_id
        assert box_id >= 1"""
reference = """def ensure_item_in_one_box(assignments: DSList(length=6, elem_type=BoxAssignment)):
    for i in range(1, 7):
        assert assignments[i].box_id >= 1"""
result = calc_codebleu([prediction], [reference], lang="python", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)
print(result)