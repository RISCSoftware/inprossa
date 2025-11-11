code_cutting_machine = """
def cutting_machine(board_list: DSList(N_BOARDS, Board),
                    cuts_list_list: DSList(N_BOARDS, CutList)):
    pieces: DSList(N_PIECES, Piece)
    for board_index, board in enumerate(board_list):
        cut_list : DSList(MAX_N_CUTS_PER_BOARD, DSInt(0, MAX_BOARD_LENGTH)) = cuts_list_list[board_index]
        assert cut_list[1] == 0
        assert cut_list[MAX_N_CUTS_PER_BOARD] == board.length
        curved_intervals_board : DSList(MAX_N_CUTS_PER_BOARD - 1, Interval) = board.curved_intervals
        for interval in curved_intervals_board:
            assert any(interval.start <= cut and cut <= interval.end for cut in cut_list)
        for cut_index in range(len(cut_list)):
            # Impose ordered cuts
            if cut_index > 1:
                piece_length = cut_list[cut_index - 1] - cut_list[cut_index]
                assert piece_length >= 0
                if piece_length == 0:
                    assert cut_list[cut_index] == board.length
                    # No piece of length 0 unless it is the last piece
                    # This reduces the spaces of solutions
                    # But also removes valid solutions if there is more than one reordering machine (unless the filtering machine puts all the empty pieces at the end, instead of just replacing discarded pieces with empty pieces)
                if all(
                   interval.start <= cut_list[cut_index] and
                   cut_list[cut_index - 1] <= interval.end
                   for interval in board.bad_intervals
                   ):
                    quality = True
                else:
                    quality = False
                pieces[(board_index - 1) * (MAX_N_CUTS_PER_BOARD - 1) + cut_index] = {"quality": quality, "length": piece_length}
    return pieces
"""
