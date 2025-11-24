from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Translator.WoodCuttingPipeline.check_machine import code_check_machine
from Translator.Objects.MinizincRunner import MiniZincRunner

# ===== Example usage =====
if __name__ == "__main__":
    code = """
# LEN : int = 10
# NAMEE : int = 3
MyInt = DSInt(0, 10)
MyVec = DSList(length = 3, elem_type = MyInt)
# PersonRec = DSRecord({"name":float,"age":MyVec})
# a : PersonRec
# a.name = 5.0
# a.name = a.name + 2.
c: MyVec
c[1] = 3
c[1] = 3 + c[1]
c[2] = c[1] + 4
b : int
b = 3
b = b + 4
"""
#     code = """
# a: int
# b: int
# a = 5
# a = a + 3
# assert a == 7
# def my_f(x: int, y: int):
#     z = x * y + 2
#     a = 2 * z
#     return a
# b = my_f(2, 3)
# """
    code = """
a : DSList(4, int)
for b in a:
    b = 2
"""
    code = """
a : DSList(4, int)
b : int
for i in range(1, 4):
    a[i] = i * 2
    b = a[i] + b
"""
    code = """
MyRec = DSRecord({
    "field1": int
    })
a : DSList(4, MyRec)
b : int = 0
for i in range(1, 5):
    a[i].field1 = i * 2
    b = a[i].field1 + b
"""
    code = """
pieces : DSList(2, DSList(1, int))
pieces = [[1],[2]]
pieces[2] = pieces[1]
"""
    code = """
    
N_BOARDS : int = 3
MAX_BOARD_LENGTH : int = 30
MAX_N_INTERVALS : int = 5
# Maximum number of bad (or curved) intervals per board
MAX_N_CUTS_PER_BOARD : int = 10
# Maximum number of cuts per board (including the two fixed cuts at the start and end of the board)

N_PIECES : int = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1)
# Total number of pieces to be obtained from all boards
BEAM_LENGTH : int = 10
# Length of the beams to be produced
BEAM_DEPTH : int = 5
# Number of layers of pieces in each beam
MAX_PIECES_PER_BEAM : int = 5
# Maximum number of pieces per beam layer
MIN_DIST_BETWEEN_PIECES : int = 1
FORBIDDEN_INTERVALS : DSList(2, DSList(2, int)) = [[3,4], [7,8]]
Interval = DSRecord({
    "start": DSInt(0, MAX_BOARD_LENGTH),
    "end": DSInt(0, MAX_BOARD_LENGTH)
})

Board = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "bad_intervals": DSList(MAX_N_INTERVALS, Interval),
    "curved_intervals": DSList(MAX_N_INTERVALS, Interval)
})
GIVEN_INITIAL_BOARDS : DSList(3, Board) = [
    Board(length=20,
          bad_intervals=[Interval(5,6+4), Interval(15,16)],
          curved_intervals=[Interval(10,12)]
    ),
    Board(length=15,
          bad_intervals=[Interval(3,4)],
          curved_intervals=[Interval(7,9)],
    ),
    Board(length=25,
          bad_intervals=[Interval(8,10), Interval(18,20)],
          curved_intervals=[Interval(5,7), Interval(12,14)]
    )
]

"""
    code = """
BoxAssignment = DSRecord({
    "box_id": int,
    "x": int,
    "y": int
})
assignments: DSList(length=6, elem_type=BoxAssignment)
used_boxes : DSList(length=6, elem_type=DSBool())
assignment: BoxAssignment
for i in range(1, 7):
    used_boxes[i] = 0
for i in range(1, 7):
    assignment = assignments[i]
    used_boxes[assignment.box_id] = 1

"""
    # code = code_check_machine
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print("\n")
    print(model)
    print("\n")

    
    runner = MiniZincRunner()
    result = runner.run(model)
    print(result)
