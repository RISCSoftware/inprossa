code_pipeline = f"""


initial_boards: DSList(N_BOARDS, Board) = GIVEN_INITIAL_BOARDS


# Swapping boards

swapping_decisions_boards: DSList(N_BOARDS - 1, bool)
swapped_boards = reordering_board_machine(initial_boards, swapping_decisions_boards) # It's necessary to specify the length if we want to use it for boards and pieces


# Cutting boards

cuts_list_list: DSList(N_BOARDS, CutList)
pieces = cutting_machine(swapped_boards, cuts_list_list)


# Filtering pieces

keep_decisions: DSList(N_PIECES, bool)
filtered_pieces = filtering_machine(pieces, keep_decisions)

# Reordering pieces

swapping_decisions: DSList(N_PIECES - 1, bool)
reordered_pieces = reordering_piece_machine(filtered_pieces, swapping_decisions)


# Checking pieces

checking_machine(reordered_pieces)
"""
