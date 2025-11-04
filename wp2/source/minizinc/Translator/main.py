from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Translator.WoodCuttingPipeline.check_machine import code_check_machine


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
    # code = code_check_machine
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print("\n")
    print(model)
    print("\n")




class Interval:
    def __init__(self, start:int, end:int):
        self.start = start
        self.end = end

    def impose_ordered(self):
        assert self.start <= self.end

    def impose_contained(self, length):
        assert self.start <= length
        assert self.end <= length

N_BAD_INTERVALS = 5

class Board:
    def __init__(self, length: int, bad_intervals: list[Interval]):
        self.length = length
        self.bad_intervals = bad_intervals

    def impose_ordered(self):
        for interval in self.bad_intervals:
            interval.impose_ordered()

    def impose_contained(self):
        for interval in self.bad_intervals:
            interval.impose_contained(self.length)

