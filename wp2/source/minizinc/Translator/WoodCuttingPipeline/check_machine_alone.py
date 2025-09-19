
code_check_machine = f"""
MAX_LENGTH = 10
MAX_DEPTH = 5
MAX_N_LENGTH = 5
MIN_DIST = 1
PIECES = [2,5,3,1,9,5,3,2]
TRY = [0,1,2,3,4,5,6,7]
FORBIDDEN_INTERVALS = [[3,4], [7,8]]
depth = 0
length = 0
n_length = 0
n_prev_layer = 0
new_beam = True
for piece in PIECES:
    length = length + piece
    n_length = n_length + 1
    assert length <= MAX_LENGTH
    if length == MAX_LENGTH:
        depth = depth + 1
        n_prev_layer = n_length
        n_length = 0
        length = 0
        if depth == MAX_DEPTH:
            new_beam = True
            depth = 0
    else:
        new_beam = False
        for i in range(1, MAX_N_LENGTH):
            if i < n_prev_layer:
                start = current_index - n_length - n_prev_layer + 1
                end = start + i - 1
                s = 0
                for j in range(1, MAX_N_LENGTH):
                    if start <= j:
                        if j <= end:
                            s = s + PIECES[j]
                assert s - length >= MIN_DIST
                assert length - s >= MIN_DIST


"""