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
    code = """
Item = DSRecord({
    "value": int,
    "weight": DSInt()
})

ITEM1 : Item
ITEM1.value = 15
ITEM1.weight = 12
ITEM2 : Item
ITEM2.value = 50
ITEM2.weight = 70
ITEM3 : Item
ITEM3.value = 80
ITEM3.weight = 100
ITEM4 : Item
ITEM4.value = 80
ITEM4.weight = 20
ITEM5 : Item
ITEM5.value = 20
ITEM5.weight = 12
ITEM6 : Item
ITEM6.value = 25
ITEM6.weight = 5
Items = DSList(length = 6, elem_type = Item)
ITEMS : Items = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 7
MAX_WEIGHT : int = 110
ChosenItemsArray = DSList(6, DSBool())
chosen_items : ChosenItemsArray

def pack_item(items: Items, chosen_items: ChosenItemsArray):
    accumulated_weight = 0
    objective: int = 0
    for i, item in enumerate(items):
        if chosen_items[i]:
            accumulated_weight = accumulated_weight + item.weight
            objective = objective - item.value
    return accumulated_weight

accumulated_weight = pack_item(ITEMS, chosen_items)

assert accumulated_weight > 0
assert accumulated_weight < MAX_WEIGHT
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

