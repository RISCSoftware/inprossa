code_cutting_machine = f"""
def cutting_machine(board_list: DSList(N_BOARDS, Board),
                    cuts_list_list: DSList(N_BOARDS, CutList)):
    pieces: DSList(N_PIECES, Piece)
    for board_index, board in enumerate(board_list):
        cut_list = cuts_list_list[board_index]
        assert cut_list[0] == 0
        assert cut_list[MAX_N_CUTS_PER_BOARD] == board.length
        for interval in board.curved_intervals:
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
                quality = all(
                   interval.start <= cut_list[cut_index] and
                   cut_list[cut_index - 1] <= interval.end
                   for interval in board.bad_intervals
                   )
                pieces[(board_index - 1) * (MAX_N_CUTS_PER_BOARD - 1) + cut_index - 1] = Piece(piece_length, quality)
    return pieces
"""
