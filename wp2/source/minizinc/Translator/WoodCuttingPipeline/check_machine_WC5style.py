
code_check_machine = f"""
def checking_machine(pieces: list[Piece]):
    depth = 0
    length = 0
    n_length = 0
    n_prev_layer = 0
    new_beam = True
    all_lengths : Annotated[list[int], "len = N_PIECES"]
    for piece_index, piece in enumerate(pieces):
        length = length + piece.length
        assert all_lengths[piece_index] == length
        # TODO ASSERTION HERE IS BEETER
        n_length = n_length + 1
        assert length <= BEAM_LENGTH
        if length == BEAM_LENGTH:
            depth = depth + 1
            n_prev_layer = n_length
            n_length = 0
            length = 0
            if depth == BEAM_DEPTH:
                new_beam = True
                depth = 0
        else:
            new_beam = False
            for i in range(1, MAX_PIECES_PER_BEAM):
                if i < n_prev_layer:
                    start = current_index - n_length - n_prev_layer + 1
                    end = start + i - 1
                    for j in range(1, MAX_PIECES_PER_BEAM):
                        # the language can be made more elegant taking in for from i to j, and automatically translating into this if lower and upper bounds are known
                        if start <= j:
                            if j <= end:
                                assert abs(all_lengths[j] - length) >= MIN_DIST_BETWEEN_PIECES
            # Check forbidden intervals
            for interval in FORBIDDEN_INTERVALS:
                assert not (interval[0] <= length and length <= interval[1])
"""