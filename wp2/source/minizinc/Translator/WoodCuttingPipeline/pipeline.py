code_pipeline = f"""


initial_boards: list[Board] = GIVEN_INITIAL_BOARDS
N_BOARDS = len(initial_boards)
N_PIECES = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1) # First and last cuts are fixed


# Swapping boards

swapping_decisions_boards: DSList(N_BOARDS - 1, bool)
swapped_boards = reordering_machine(N_BOARDS, initial_boards, swapping_decisions_boards) # It's necessary to specify the length if we want to use it for boards and pieces


# Cutting boards

cuts_list_list: DSList(N_BOARDS, CutList(MAX_N_CUTS_PER_BOARD))
pieces = cutting_machine(swapped_boards, cuts_list_list)


# Filtering pieces

N_PIECES = N_BOARDS * (MAX_N_CUTS_PER_BOARD - 1) # First and last cuts are fixed
keep_decisions: DSList(N_PIECES, bool)
filtered_pieces = filtering_machine(N_PIECES, pieces, keep_decisions)

# Reordering pieces

swapping_decisions: DSList(N_PIECES - 1, bool)
reordered_pieces = reordering_machine(N_PIECES, filtered_pieces, swapping_decisions)


# Checking pieces

checking_machine(reordered_pieces)
"""
