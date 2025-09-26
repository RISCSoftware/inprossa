code_reordering_machine = f"""
def reordering_machine(N_ELEMENTS: int,
                       list_to_reorder: DSList(N_ELEMENTS, Piece),
                       swapping_decisions: DSList(N_ELEMENTS - 1, bool),
                       ) -> DSList(N_ELEMENTS, Piece):
    new_list = list_to_reorder
    for i in range(N_ELEMENTS - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_piece = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_piece
    return new_list
"""
