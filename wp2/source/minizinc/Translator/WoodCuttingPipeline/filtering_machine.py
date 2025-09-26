code_filtering_machine = f"""
def filtering_machine(N_ELEMENTS: int,
                      list_to_filter: DSList(N_ELEMENTS, Piece),
                      keep_decisions: DSList(N_ELEMENTS, bool),
                      ):
    # Initialize filtered list with empty pieces
    filtered_list : DSList(N_ELEMENTS, Piece)
    for i in range(N_ELEMENTS):
        if keep_decisions[i]:
            assert list_to_filter[i].quality == True
            filtered_list[i] = list_to_filter[i]
        else:
            objective += list_to_filter[i].length
            filtered_list[i] = Piece()

    return filtered_list
"""
