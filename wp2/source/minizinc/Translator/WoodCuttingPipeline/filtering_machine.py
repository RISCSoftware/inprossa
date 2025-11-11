code_filtering_machine = """
def filtering_machine(list_to_filter: DSList(N_PIECES, Piece),
                      keep_decisions: DSList(N_PIECES, bool),
                      ):
    # Initialize filtered list with empty pieces
    filtered_list : DSList(N_PIECES, Piece)
    for i in range(N_PIECES):
        if keep_decisions[i]:
            assert list_to_filter[i].quality == True
            filtered_list[i] = list_to_filter[i]
        else:
            objective += list_to_filter[i].length
            filtered_list[i] = {"quality": True, "length": 0}

    return filtered_list
"""
