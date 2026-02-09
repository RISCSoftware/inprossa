dsl_code = """
# --- Objects ---
Item = DSRecord({
    "value": DSInt(lb=1, ub=80),
    "weight": DSInt(lb=1, ub=100)
})

# --- Constants ---
ITEM1 : Item = {\"value": 15, \"weight": 12}
ITEM2 : Item = {\"value": 50, \"weight": 70}
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
ITEMS : DSList(length=6, elem_type=Item) = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 6
MAX_WEIGHT : int = 110

# --- Decision Variables ---
chosen_items : DSList(length=6, elem_type=DSBool())
accumulated_value : DSInt(lb=0)
accumulated_weight : DSInt(lb=0, ub=MAX_WEIGHT)

# --- Constraints ---
def pack_item(items: DSList(length=6, elem_type=Item),
                chosen_items: DSList(length=6, elem_type=DSBool())):
    accumulated_weight: int = 0
    accumulated_value: int = 0
    for i in range(1, N_ITEMS + 1):
        if chosen_items[i]:
            item_p : Item = items[i]
            accumulated_weight = accumulated_weight + items[i].weight
            accumulated_value = accumulated_value + items[i].value
    return accumulated_value, accumulated_weight

accumulated_value, accumulated_weight = pack_item(ITEMS, chosen_items)
assert accumulated_weight >= 0
assert accumulated_weight < MAX_WEIGHT
assert accumulated_value >= 0
maximize(accumulated_value)


"""


from Translator.Objects.MiniZincTranslator import MiniZincTranslator

if __name__ == "__main__":
    translator = MiniZincTranslator(dsl_code)
    model = translator.unroll_translation()
    print("\n")
    print(model)
    print("\n")
    from Tools.MinizincRunner import MiniZincRunner
    runner = MiniZincRunner()
    result = runner.run(model)
    print(result)