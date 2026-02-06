from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner

code = """
# --- Objects ---
X_Y_Position = DSRecord({"x" : DSInt(lb=0, ub=12), "y" : DSInt(lb=0, ub=5)})

# --- Constants and Decision Variables ---
N_ITEMS : int = 9
item_box_assignments : DSList(length=9, elem_type=DSInt(lb=1, ub=9))
x_y_positions : DSList(length=9, elem_type=X_Y_Position)

# --- Incorrect Code ---
def no_overlap(
    item_box_assignments: DSList(length=9, elem_type=DSInt(lb=1, ub=9)),
    x_y_positions: DSList(length=9, elem_type=X_Y_Position)
) -> None:
    if 3 == N_ITEMS:
        pos_i: X_Y_Position = x_y_positions[3]
    pos_i: X_Y_Position = x_y_positions[2]

no_overlap(item_box_assignments, x_y_positions)

"""
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")

runner = MiniZincRunner()
result = runner.run(model)
print(result)