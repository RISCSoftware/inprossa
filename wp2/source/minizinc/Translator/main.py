from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
    code = """
a : DSList(7, DSInt(0, 10))
MyInt = DSList(7, DSList(7, DSInt(0, 10)))
LEN : int = 10
NAMEE : int = LEN + 3
MyVec = DSList(LEN, elem_type = int)
MyyVec = DSList(length = NAMEE, elem_type = MyInt)
PersonRec = DSRecord({"name":string,"age":MyVec})
oneofmyints : MyInt = 3
"""
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)




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

