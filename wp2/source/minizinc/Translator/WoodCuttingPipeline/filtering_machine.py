code_filtering_machine = f"""
def filtering_machine(list_to_filter: list[Piece],
                      keep_decisions: list[bool],
                      N_ELEMENTS: int):
    # Initialize filtered list with empty pieces
    filtered_list = [Piece()] * len(list_to_filter)
    for i in range(N_ELEMENTS):
        if keep_decisions[i]:
            assert list_to_filter[i].quality == True
            filtered_list[i] = list_to_filter[i]
        else:
            filtered_list[i] = Piece()
    return filtered_list
"""
