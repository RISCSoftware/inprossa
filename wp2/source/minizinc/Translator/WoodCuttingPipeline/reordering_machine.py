code_reordering_machine = f"""
def reordering_machine(list_to_reorder: list[Piece, Board],
                       swapping_decisions: list[bool],
                       N_ELEMENTS: int):
    new_list = list_to_reorder
    for i in range(N_ELEMENTS - 1): # Number of swapping decisions
        if swapping_decisions[i]:
            aux_piece = new_list[i]
            new_list[i] = new_list[i + 1]
            new_list[i + 1] = aux_piece
    return new_list
"""
