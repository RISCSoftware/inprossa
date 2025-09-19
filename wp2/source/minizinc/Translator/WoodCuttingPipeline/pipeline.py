from typing import Annotated

code_pipeline = f"""
initial_boards: list[Board] = GIVEN_BOARDS
N_BOARDS = len(initial_boards)


# Swapping boards

swapping_decisions: Annotated[list[bool], "len = N_BOARDS - 1"]
swapped_boards = reordering_machine(initial_boards, swapping_decisions, N_BOARDS) # It's necessary to specify the length if we want to use it for boards and pieces


# Cutting boards

cuts_list_list: Annotated[list[Cuts(MAX_N_CUTS)], "len = N_BOARDS"]
pieces = cutting_machine(swapped_boards, cuts_list_list)


# Filtering pieces

N_PIECES = N_BOARDS * (MAX_N_CUTS - 1) # First and last cuts are fixed
keep_decisions: Annotated[list[bool], "len = N_PIECES"]
filtered_pieces = filtering_machine(pieces, keep_decisions, N_PIECES)


# Reordering pieces

swapping_decisions: Annotated[list[bool], "len = N_PIECES - 1"]
reordered_pieces = reordering_machine(filtered_pieces, swapping_decisions, N_PIECES)


# Checking pieces

checking_machine(reordered_pieces)
"""
