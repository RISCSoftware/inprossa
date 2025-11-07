from Translator.Objects.MiniZincTranslator import MiniZincTranslator

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
translator = MiniZincTranslator(code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")