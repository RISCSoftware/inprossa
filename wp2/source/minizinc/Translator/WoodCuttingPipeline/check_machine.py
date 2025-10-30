
code_check_machine = """
Piece = DSRecord({
    "length": DSInt(0, MAX_BOARD_LENGTH),
    "quality": DSBool()
})
MAX_BOARD_LENGTH : int = 10
MAX_N_INTERVALS : int = 5
MAX_PIECES_PER_BEAM : int = 2
MIN_DIST_BETWEEN_PIECES : int = 2
MAX_PIECES : int = 10
BEAM_LENGTH : int = 10
BEAM_DEPTH : int = 3
FORBIDDEN_INTERVALS : DSList(2, DSList(2, int)) = [[3,4], [7,8]]
pieces : DSList(5, elem_type = Piece)
def checking_machine(pieces: DSList(MAX_PIECES, elem_type = Piece)):
    depth = 0
    length = 0
    n_length = 0
    n_prev_layer = 0
    new_beam = True
    for piece in pieces:
        length = length + piece.length
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
                    s = 0
                    for j in range(1, MAX_PIECES_PER_BEAM):
                        # the language can be made more elegant taking in for from i to j, and automatically translating into this if lower and upper bounds are known
                        if start <= j:
                            if j <= end:
                                s = s + pieces[j].length
                                assert abs(s - length) >= MIN_DIST_BETWEEN_PIECES
            # Check forbidden intervals
            for interval in FORBIDDEN_INTERVALS:
                assert not (interval[0] <= length and length <= interval[1])
"""