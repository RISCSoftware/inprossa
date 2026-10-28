type Interval = record(
    0..MAX_BOARD_LENGTH: start,
    0..MAX_BOARD_LENGTH: end
);
type Board = record(
    0..MAX_BOARD_LENGTH: length,
    array[1..1] of Interval: bad_intervals,
    array[1..1] of Interval: curved_intervals
);
type Piece = record(
    0..MAX_BOARD_LENGTH: length,
    0..1: quality
);
type CutList = record(
    array[1..3] of 0..MAX_BOARD_LENGTH: position_list
);
predicate checking_machine(array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): input_1, array[1..5] of var int: current_index, array[1..9] of var int: depth, array[1..5] of array[1..4] of var 0..BEAM_LENGTH: layer_lengths, array[1..9] of var int: length, array[1..9] of var int: n_length, array[1..5] of var int: n_prev_layer, array[1..5] of var int: new_beam, array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): pieces, array[1..17] of array[1..4] of var 0..BEAM_LENGTH: prev_layer_lengths, array[1..16] of var int: s, array[1..5] of var int: total_depth) =
    forall([
        pieces[1][1].length = input_1[1].length,
        pieces[1][1].quality = input_1[1].quality,
        pieces[1][2].length = input_1[2].length,
        pieces[1][2].quality = input_1[2].quality,
        pieces[1][3].length = input_1[3].length,
        pieces[1][3].quality = input_1[3].quality,
        pieces[1][4].length = input_1[4].length,
        pieces[1][4].quality = input_1[4].quality,
        depth[1] = 0,
        total_depth[1] = 0,
        length[1] = 0,
        n_length[1] = 0,
        n_prev_layer[1] = 0,
        new_beam[1] = 1,
        current_index[1] = 0,
        current_index[2] = (current_index[1] + 1),
        length[2] = (length[1] + pieces[1][1].length),
        (((n_length[1] + 1) != 1) /\ (pieces[1][1].length > 0) -> layer_lengths[2][1] = layer_lengths[1][1]),
        (((n_length[1] + 1) != 2) /\ (pieces[1][1].length > 0) -> layer_lengths[2][2] = layer_lengths[1][2]),
        (((n_length[1] + 1) != 3) /\ (pieces[1][1].length > 0) -> layer_lengths[2][3] = layer_lengths[1][3]),
        (((n_length[1] + 1) != 4) /\ (pieces[1][1].length > 0) -> layer_lengths[2][4] = layer_lengths[1][4]),
        ((pieces[1][1].length > 0) -> layer_lengths[2][(n_length[1] + 1)] = length[2]),
        ((pieces[1][1].length > 0) -> n_length[2] = (n_length[1] + 1)),
        ((not (pieces[1][1].length > 0)) -> layer_lengths[2] = layer_lengths[1]),
        ((not (pieces[1][1].length > 0)) -> n_length[2] = n_length[1]),
        (length[2] <= BEAM_LENGTH),
        ((length[2] = BEAM_LENGTH) -> depth[2] = (depth[1] + 1)),
        ((length[2] = BEAM_LENGTH) -> total_depth[2] = (total_depth[1] + 1)),
        ((0 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[2][2] = prev_layer_lengths[1][2]),
        ((0 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[2][3] = prev_layer_lengths[1][3]),
        ((0 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[2][4] = prev_layer_lengths[1][4]),
        ((0 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[2][1] = layer_lengths[2][1]),
        ((not (0 < n_length[2])) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[2] = prev_layer_lengths[1]),
        ((1 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[3][1] = prev_layer_lengths[2][1]),
        ((1 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[3][3] = prev_layer_lengths[2][3]),
        ((1 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[3][4] = prev_layer_lengths[2][4]),
        ((1 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[3][2] = layer_lengths[2][2]),
        ((not (1 < n_length[2])) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[3] = prev_layer_lengths[2]),
        ((2 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[4][1] = prev_layer_lengths[3][1]),
        ((2 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[4][2] = prev_layer_lengths[3][2]),
        ((2 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[4][4] = prev_layer_lengths[3][4]),
        ((2 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[4][3] = layer_lengths[2][3]),
        ((not (2 < n_length[2])) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[4] = prev_layer_lengths[3]),
        ((3 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[5][1] = prev_layer_lengths[4][1]),
        ((3 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[5][2] = prev_layer_lengths[4][2]),
        ((3 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[5][3] = prev_layer_lengths[4][3]),
        ((3 < n_length[2]) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[5][4] = layer_lengths[2][4]),
        ((not (3 < n_length[2])) /\ (length[2] = BEAM_LENGTH) -> prev_layer_lengths[5] = prev_layer_lengths[4]),
        ((length[2] = BEAM_LENGTH) -> n_prev_layer[2] = n_length[2]),
        ((length[2] = BEAM_LENGTH) -> n_length[3] = 0),
        ((length[2] = BEAM_LENGTH) -> length[3] = 0),
        ((depth[2] = BEAM_DEPTH) /\ (length[2] = BEAM_LENGTH) -> new_beam[2] = 1),
        ((depth[2] = BEAM_DEPTH) /\ (length[2] = BEAM_LENGTH) -> depth[3] = 0),
        ((not (depth[2] = BEAM_DEPTH)) /\ (length[2] = BEAM_LENGTH) -> new_beam[2] = new_beam[1]),
        ((not (depth[2] = BEAM_DEPTH)) /\ (length[2] = BEAM_LENGTH) -> depth[3] = depth[2]),
        ((not (length[2] = BEAM_LENGTH)) -> new_beam[2] = 0),
        ((0 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[1] = prev_layer_lengths[1][1]),
        ((0 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (((s[1] - length[2]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[2] - s[1]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((1 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[2] = prev_layer_lengths[1][2]),
        ((1 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (((s[2] - length[2]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[2] - s[2]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (1 < n_prev_layer[1])) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[2] = s[1]),
        ((2 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[3] = prev_layer_lengths[1][3]),
        ((2 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (((s[3] - length[2]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[2] - s[3]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (2 < n_prev_layer[1])) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[3] = s[2]),
        ((3 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[4] = prev_layer_lengths[1][4]),
        ((3 < n_prev_layer[1]) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (((s[4] - length[2]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[2] - s[4]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (3 < n_prev_layer[1])) /\ (depth[1] >= 1) /\ (pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> s[4] = s[3]),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[1][1] <= length[2]) /\ (length[2] <= FORBIDDEN_INTERVALS[1][2])))),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[2][1] <= length[2]) /\ (length[2] <= FORBIDDEN_INTERVALS[2][2])))),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[3][1] <= length[2]) /\ (length[2] <= FORBIDDEN_INTERVALS[3][2])))),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[4][1] <= length[2]) /\ (length[2] <= FORBIDDEN_INTERVALS[4][2])))),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (length[2] > BEAM_SKIP_START)),
        ((pieces[1][1].length > 0) /\ (not (length[2] = BEAM_LENGTH)) -> (length[2] < (BEAM_LENGTH - BEAM_SKIP_END))),
        ((not (length[2] = BEAM_LENGTH)) -> total_depth[2] = total_depth[1]),
        ((not (length[2] = BEAM_LENGTH)) -> n_prev_layer[2] = n_prev_layer[1]),
        ((not (length[2] = BEAM_LENGTH)) -> prev_layer_lengths[5] = prev_layer_lengths[1]),
        ((not (length[2] = BEAM_LENGTH)) -> depth[3] = depth[1]),
        ((not (length[2] = BEAM_LENGTH)) -> n_length[3] = n_length[2]),
        ((not (length[2] = BEAM_LENGTH)) -> length[3] = length[2]),
        current_index[3] = (current_index[2] + 1),
        length[4] = (length[3] + pieces[1][2].length),
        (((n_length[3] + 1) != 1) /\ (pieces[1][2].length > 0) -> layer_lengths[3][1] = layer_lengths[2][1]),
        (((n_length[3] + 1) != 2) /\ (pieces[1][2].length > 0) -> layer_lengths[3][2] = layer_lengths[2][2]),
        (((n_length[3] + 1) != 3) /\ (pieces[1][2].length > 0) -> layer_lengths[3][3] = layer_lengths[2][3]),
        (((n_length[3] + 1) != 4) /\ (pieces[1][2].length > 0) -> layer_lengths[3][4] = layer_lengths[2][4]),
        ((pieces[1][2].length > 0) -> layer_lengths[3][(n_length[3] + 1)] = length[4]),
        ((pieces[1][2].length > 0) -> n_length[4] = (n_length[3] + 1)),
        ((not (pieces[1][2].length > 0)) -> layer_lengths[3] = layer_lengths[2]),
        ((not (pieces[1][2].length > 0)) -> n_length[4] = n_length[3]),
        (length[4] <= BEAM_LENGTH),
        ((length[4] = BEAM_LENGTH) -> depth[4] = (depth[3] + 1)),
        ((length[4] = BEAM_LENGTH) -> total_depth[3] = (total_depth[2] + 1)),
        ((0 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[6][2] = prev_layer_lengths[5][2]),
        ((0 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[6][3] = prev_layer_lengths[5][3]),
        ((0 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[6][4] = prev_layer_lengths[5][4]),
        ((0 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[6][1] = layer_lengths[3][1]),
        ((not (0 < n_length[4])) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[6] = prev_layer_lengths[5]),
        ((1 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[7][1] = prev_layer_lengths[6][1]),
        ((1 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[7][3] = prev_layer_lengths[6][3]),
        ((1 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[7][4] = prev_layer_lengths[6][4]),
        ((1 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[7][2] = layer_lengths[3][2]),
        ((not (1 < n_length[4])) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[7] = prev_layer_lengths[6]),
        ((2 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[8][1] = prev_layer_lengths[7][1]),
        ((2 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[8][2] = prev_layer_lengths[7][2]),
        ((2 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[8][4] = prev_layer_lengths[7][4]),
        ((2 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[8][3] = layer_lengths[3][3]),
        ((not (2 < n_length[4])) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[8] = prev_layer_lengths[7]),
        ((3 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[9][1] = prev_layer_lengths[8][1]),
        ((3 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[9][2] = prev_layer_lengths[8][2]),
        ((3 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[9][3] = prev_layer_lengths[8][3]),
        ((3 < n_length[4]) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[9][4] = layer_lengths[3][4]),
        ((not (3 < n_length[4])) /\ (length[4] = BEAM_LENGTH) -> prev_layer_lengths[9] = prev_layer_lengths[8]),
        ((length[4] = BEAM_LENGTH) -> n_prev_layer[3] = n_length[4]),
        ((length[4] = BEAM_LENGTH) -> n_length[5] = 0),
        ((length[4] = BEAM_LENGTH) -> length[5] = 0),
        ((depth[4] = BEAM_DEPTH) /\ (length[4] = BEAM_LENGTH) -> new_beam[3] = 1),
        ((depth[4] = BEAM_DEPTH) /\ (length[4] = BEAM_LENGTH) -> depth[5] = 0),
        ((not (depth[4] = BEAM_DEPTH)) /\ (length[4] = BEAM_LENGTH) -> new_beam[3] = new_beam[2]),
        ((not (depth[4] = BEAM_DEPTH)) /\ (length[4] = BEAM_LENGTH) -> depth[5] = depth[4]),
        ((length[4] = BEAM_LENGTH) -> s[8] = s[4]),
        ((not (length[4] = BEAM_LENGTH)) -> new_beam[3] = 0),
        ((0 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[5] = prev_layer_lengths[5][1]),
        ((0 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (((s[5] - length[4]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[4] - s[5]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (0 < n_prev_layer[2])) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[5] = s[4]),
        ((1 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[6] = prev_layer_lengths[5][2]),
        ((1 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (((s[6] - length[4]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[4] - s[6]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (1 < n_prev_layer[2])) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[6] = s[5]),
        ((2 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[7] = prev_layer_lengths[5][3]),
        ((2 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (((s[7] - length[4]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[4] - s[7]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (2 < n_prev_layer[2])) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[7] = s[6]),
        ((3 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[8] = prev_layer_lengths[5][4]),
        ((3 < n_prev_layer[2]) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (((s[8] - length[4]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[4] - s[8]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (3 < n_prev_layer[2])) /\ (depth[3] >= 1) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[8] = s[7]),
        ((not (depth[3] >= 1)) /\ (pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> s[8] = s[4]),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[1][1] <= length[4]) /\ (length[4] <= FORBIDDEN_INTERVALS[1][2])))),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[2][1] <= length[4]) /\ (length[4] <= FORBIDDEN_INTERVALS[2][2])))),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[3][1] <= length[4]) /\ (length[4] <= FORBIDDEN_INTERVALS[3][2])))),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[4][1] <= length[4]) /\ (length[4] <= FORBIDDEN_INTERVALS[4][2])))),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (length[4] > BEAM_SKIP_START)),
        ((pieces[1][2].length > 0) /\ (not (length[4] = BEAM_LENGTH)) -> (length[4] < (BEAM_LENGTH - BEAM_SKIP_END))),
        ((not (pieces[1][2].length > 0)) /\ (not (length[4] = BEAM_LENGTH)) -> s[8] = s[4]),
        ((not (length[4] = BEAM_LENGTH)) -> total_depth[3] = total_depth[2]),
        ((not (length[4] = BEAM_LENGTH)) -> n_prev_layer[3] = n_prev_layer[2]),
        ((not (length[4] = BEAM_LENGTH)) -> prev_layer_lengths[9] = prev_layer_lengths[5]),
        ((not (length[4] = BEAM_LENGTH)) -> depth[5] = depth[3]),
        ((not (length[4] = BEAM_LENGTH)) -> n_length[5] = n_length[4]),
        ((not (length[4] = BEAM_LENGTH)) -> length[5] = length[4]),
        current_index[4] = (current_index[3] + 1),
        length[6] = (length[5] + pieces[1][3].length),
        (((n_length[5] + 1) != 1) /\ (pieces[1][3].length > 0) -> layer_lengths[4][1] = layer_lengths[3][1]),
        (((n_length[5] + 1) != 2) /\ (pieces[1][3].length > 0) -> layer_lengths[4][2] = layer_lengths[3][2]),
        (((n_length[5] + 1) != 3) /\ (pieces[1][3].length > 0) -> layer_lengths[4][3] = layer_lengths[3][3]),
        (((n_length[5] + 1) != 4) /\ (pieces[1][3].length > 0) -> layer_lengths[4][4] = layer_lengths[3][4]),
        ((pieces[1][3].length > 0) -> layer_lengths[4][(n_length[5] + 1)] = length[6]),
        ((pieces[1][3].length > 0) -> n_length[6] = (n_length[5] + 1)),
        ((not (pieces[1][3].length > 0)) -> layer_lengths[4] = layer_lengths[3]),
        ((not (pieces[1][3].length > 0)) -> n_length[6] = n_length[5]),
        (length[6] <= BEAM_LENGTH),
        ((length[6] = BEAM_LENGTH) -> depth[6] = (depth[5] + 1)),
        ((length[6] = BEAM_LENGTH) -> total_depth[4] = (total_depth[3] + 1)),
        ((0 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[10][2] = prev_layer_lengths[9][2]),
        ((0 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[10][3] = prev_layer_lengths[9][3]),
        ((0 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[10][4] = prev_layer_lengths[9][4]),
        ((0 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[10][1] = layer_lengths[4][1]),
        ((not (0 < n_length[6])) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[10] = prev_layer_lengths[9]),
        ((1 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[11][1] = prev_layer_lengths[10][1]),
        ((1 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[11][3] = prev_layer_lengths[10][3]),
        ((1 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[11][4] = prev_layer_lengths[10][4]),
        ((1 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[11][2] = layer_lengths[4][2]),
        ((not (1 < n_length[6])) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[11] = prev_layer_lengths[10]),
        ((2 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[12][1] = prev_layer_lengths[11][1]),
        ((2 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[12][2] = prev_layer_lengths[11][2]),
        ((2 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[12][4] = prev_layer_lengths[11][4]),
        ((2 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[12][3] = layer_lengths[4][3]),
        ((not (2 < n_length[6])) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[12] = prev_layer_lengths[11]),
        ((3 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[13][1] = prev_layer_lengths[12][1]),
        ((3 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[13][2] = prev_layer_lengths[12][2]),
        ((3 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[13][3] = prev_layer_lengths[12][3]),
        ((3 < n_length[6]) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[13][4] = layer_lengths[4][4]),
        ((not (3 < n_length[6])) /\ (length[6] = BEAM_LENGTH) -> prev_layer_lengths[13] = prev_layer_lengths[12]),
        ((length[6] = BEAM_LENGTH) -> n_prev_layer[4] = n_length[6]),
        ((length[6] = BEAM_LENGTH) -> n_length[7] = 0),
        ((length[6] = BEAM_LENGTH) -> length[7] = 0),
        ((depth[6] = BEAM_DEPTH) /\ (length[6] = BEAM_LENGTH) -> new_beam[4] = 1),
        ((depth[6] = BEAM_DEPTH) /\ (length[6] = BEAM_LENGTH) -> depth[7] = 0),
        ((not (depth[6] = BEAM_DEPTH)) /\ (length[6] = BEAM_LENGTH) -> new_beam[4] = new_beam[3]),
        ((not (depth[6] = BEAM_DEPTH)) /\ (length[6] = BEAM_LENGTH) -> depth[7] = depth[6]),
        ((length[6] = BEAM_LENGTH) -> s[12] = s[8]),
        ((not (length[6] = BEAM_LENGTH)) -> new_beam[4] = 0),
        ((0 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[9] = prev_layer_lengths[9][1]),
        ((0 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (((s[9] - length[6]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[6] - s[9]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (0 < n_prev_layer[3])) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[9] = s[8]),
        ((1 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[10] = prev_layer_lengths[9][2]),
        ((1 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (((s[10] - length[6]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[6] - s[10]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (1 < n_prev_layer[3])) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[10] = s[9]),
        ((2 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[11] = prev_layer_lengths[9][3]),
        ((2 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (((s[11] - length[6]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[6] - s[11]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (2 < n_prev_layer[3])) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[11] = s[10]),
        ((3 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[12] = prev_layer_lengths[9][4]),
        ((3 < n_prev_layer[3]) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (((s[12] - length[6]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[6] - s[12]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (3 < n_prev_layer[3])) /\ (depth[5] >= 1) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[12] = s[11]),
        ((not (depth[5] >= 1)) /\ (pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> s[12] = s[8]),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[1][1] <= length[6]) /\ (length[6] <= FORBIDDEN_INTERVALS[1][2])))),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[2][1] <= length[6]) /\ (length[6] <= FORBIDDEN_INTERVALS[2][2])))),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[3][1] <= length[6]) /\ (length[6] <= FORBIDDEN_INTERVALS[3][2])))),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[4][1] <= length[6]) /\ (length[6] <= FORBIDDEN_INTERVALS[4][2])))),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (length[6] > BEAM_SKIP_START)),
        ((pieces[1][3].length > 0) /\ (not (length[6] = BEAM_LENGTH)) -> (length[6] < (BEAM_LENGTH - BEAM_SKIP_END))),
        ((not (pieces[1][3].length > 0)) /\ (not (length[6] = BEAM_LENGTH)) -> s[12] = s[8]),
        ((not (length[6] = BEAM_LENGTH)) -> total_depth[4] = total_depth[3]),
        ((not (length[6] = BEAM_LENGTH)) -> n_prev_layer[4] = n_prev_layer[3]),
        ((not (length[6] = BEAM_LENGTH)) -> prev_layer_lengths[13] = prev_layer_lengths[9]),
        ((not (length[6] = BEAM_LENGTH)) -> depth[7] = depth[5]),
        ((not (length[6] = BEAM_LENGTH)) -> n_length[7] = n_length[6]),
        ((not (length[6] = BEAM_LENGTH)) -> length[7] = length[6]),
        current_index[5] = (current_index[4] + 1),
        length[8] = (length[7] + pieces[1][4].length),
        (((n_length[7] + 1) != 1) /\ (pieces[1][4].length > 0) -> layer_lengths[5][1] = layer_lengths[4][1]),
        (((n_length[7] + 1) != 2) /\ (pieces[1][4].length > 0) -> layer_lengths[5][2] = layer_lengths[4][2]),
        (((n_length[7] + 1) != 3) /\ (pieces[1][4].length > 0) -> layer_lengths[5][3] = layer_lengths[4][3]),
        (((n_length[7] + 1) != 4) /\ (pieces[1][4].length > 0) -> layer_lengths[5][4] = layer_lengths[4][4]),
        ((pieces[1][4].length > 0) -> layer_lengths[5][(n_length[7] + 1)] = length[8]),
        ((pieces[1][4].length > 0) -> n_length[8] = (n_length[7] + 1)),
        ((not (pieces[1][4].length > 0)) -> layer_lengths[5] = layer_lengths[4]),
        ((not (pieces[1][4].length > 0)) -> n_length[8] = n_length[7]),
        (length[8] <= BEAM_LENGTH),
        ((length[8] = BEAM_LENGTH) -> depth[8] = (depth[7] + 1)),
        ((length[8] = BEAM_LENGTH) -> total_depth[5] = (total_depth[4] + 1)),
        ((0 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[14][2] = prev_layer_lengths[13][2]),
        ((0 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[14][3] = prev_layer_lengths[13][3]),
        ((0 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[14][4] = prev_layer_lengths[13][4]),
        ((0 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[14][1] = layer_lengths[5][1]),
        ((not (0 < n_length[8])) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[14] = prev_layer_lengths[13]),
        ((1 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[15][1] = prev_layer_lengths[14][1]),
        ((1 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[15][3] = prev_layer_lengths[14][3]),
        ((1 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[15][4] = prev_layer_lengths[14][4]),
        ((1 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[15][2] = layer_lengths[5][2]),
        ((not (1 < n_length[8])) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[15] = prev_layer_lengths[14]),
        ((2 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[16][1] = prev_layer_lengths[15][1]),
        ((2 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[16][2] = prev_layer_lengths[15][2]),
        ((2 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[16][4] = prev_layer_lengths[15][4]),
        ((2 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[16][3] = layer_lengths[5][3]),
        ((not (2 < n_length[8])) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[16] = prev_layer_lengths[15]),
        ((3 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[17][1] = prev_layer_lengths[16][1]),
        ((3 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[17][2] = prev_layer_lengths[16][2]),
        ((3 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[17][3] = prev_layer_lengths[16][3]),
        ((3 < n_length[8]) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[17][4] = layer_lengths[5][4]),
        ((not (3 < n_length[8])) /\ (length[8] = BEAM_LENGTH) -> prev_layer_lengths[17] = prev_layer_lengths[16]),
        ((length[8] = BEAM_LENGTH) -> n_prev_layer[5] = n_length[8]),
        ((length[8] = BEAM_LENGTH) -> n_length[9] = 0),
        ((length[8] = BEAM_LENGTH) -> length[9] = 0),
        ((depth[8] = BEAM_DEPTH) /\ (length[8] = BEAM_LENGTH) -> new_beam[5] = 1),
        ((depth[8] = BEAM_DEPTH) /\ (length[8] = BEAM_LENGTH) -> depth[9] = 0),
        ((not (depth[8] = BEAM_DEPTH)) /\ (length[8] = BEAM_LENGTH) -> new_beam[5] = new_beam[4]),
        ((not (depth[8] = BEAM_DEPTH)) /\ (length[8] = BEAM_LENGTH) -> depth[9] = depth[8]),
        ((length[8] = BEAM_LENGTH) -> s[16] = s[12]),
        ((not (length[8] = BEAM_LENGTH)) -> new_beam[5] = 0),
        ((0 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[13] = prev_layer_lengths[13][1]),
        ((0 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (((s[13] - length[8]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[8] - s[13]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (0 < n_prev_layer[4])) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[13] = s[12]),
        ((1 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[14] = prev_layer_lengths[13][2]),
        ((1 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (((s[14] - length[8]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[8] - s[14]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (1 < n_prev_layer[4])) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[14] = s[13]),
        ((2 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[15] = prev_layer_lengths[13][3]),
        ((2 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (((s[15] - length[8]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[8] - s[15]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (2 < n_prev_layer[4])) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[15] = s[14]),
        ((3 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[16] = prev_layer_lengths[13][4]),
        ((3 < n_prev_layer[4]) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (((s[16] - length[8]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS) \/ ((length[8] - s[16]) >= GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS))),
        ((not (3 < n_prev_layer[4])) /\ (depth[7] >= 1) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[16] = s[15]),
        ((not (depth[7] >= 1)) /\ (pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> s[16] = s[12]),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[1][1] <= length[8]) /\ (length[8] <= FORBIDDEN_INTERVALS[1][2])))),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[2][1] <= length[8]) /\ (length[8] <= FORBIDDEN_INTERVALS[2][2])))),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[3][1] <= length[8]) /\ (length[8] <= FORBIDDEN_INTERVALS[3][2])))),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (not ((FORBIDDEN_INTERVALS[4][1] <= length[8]) /\ (length[8] <= FORBIDDEN_INTERVALS[4][2])))),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (length[8] > BEAM_SKIP_START)),
        ((pieces[1][4].length > 0) /\ (not (length[8] = BEAM_LENGTH)) -> (length[8] < (BEAM_LENGTH - BEAM_SKIP_END))),
        ((not (pieces[1][4].length > 0)) /\ (not (length[8] = BEAM_LENGTH)) -> s[16] = s[12]),
        ((not (length[8] = BEAM_LENGTH)) -> total_depth[5] = total_depth[4]),
        ((not (length[8] = BEAM_LENGTH)) -> n_prev_layer[5] = n_prev_layer[4]),
        ((not (length[8] = BEAM_LENGTH)) -> prev_layer_lengths[17] = prev_layer_lengths[13]),
        ((not (length[8] = BEAM_LENGTH)) -> depth[9] = depth[7]),
        ((not (length[8] = BEAM_LENGTH)) -> n_length[9] = n_length[8]),
        ((not (length[8] = BEAM_LENGTH)) -> length[9] = length[8]),
        (length[9] = 0),
        (depth[9] = 0),
        (total_depth[5] = (N_BEAMS * BEAM_DEPTH))
    ]);
predicate cutting_machine(array[1..2] of record(
    var 0..MAX_BOARD_LENGTH: length,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals
): input_1, array[1..2] of record(
    array[1..3] of var 0..MAX_BOARD_LENGTH: position_list
): input_2, array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): output_1, array[1..4] of array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals_board, array[1..1] of array[1..2] of record(
    var 0..MAX_BOARD_LENGTH: length,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals
): board_list, array[1..2] of array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals_board, array[1..2] of array[1..3] of var 0..MAX_BOARD_LENGTH: cut_list, array[1..1] of array[1..2] of record(
    array[1..3] of var 0..MAX_BOARD_LENGTH: position_list
): cuts_list_list, array[1..4] of var int: piece_length, array[1..5] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): pieces, array[1..5] of var 0..1: quality) =
    forall([
        board_list[1][1].length = input_1[1].length,
        board_list[1][1].bad_intervals[1].start = input_1[1].bad_intervals[1].start,
        board_list[1][1].bad_intervals[1].end = input_1[1].bad_intervals[1].end,
        board_list[1][1].curved_intervals[1].start = input_1[1].curved_intervals[1].start,
        board_list[1][1].curved_intervals[1].end = input_1[1].curved_intervals[1].end,
        board_list[1][2].length = input_1[2].length,
        board_list[1][2].bad_intervals[1].start = input_1[2].bad_intervals[1].start,
        board_list[1][2].bad_intervals[1].end = input_1[2].bad_intervals[1].end,
        board_list[1][2].curved_intervals[1].start = input_1[2].curved_intervals[1].start,
        board_list[1][2].curved_intervals[1].end = input_1[2].curved_intervals[1].end,
        cuts_list_list[1][1].position_list[1] = input_2[1].position_list[1],
        cuts_list_list[1][1].position_list[2] = input_2[1].position_list[2],
        cuts_list_list[1][1].position_list[3] = input_2[1].position_list[3],
        cuts_list_list[1][2].position_list[1] = input_2[2].position_list[1],
        cuts_list_list[1][2].position_list[2] = input_2[2].position_list[2],
        cuts_list_list[1][2].position_list[3] = input_2[2].position_list[3],
        quality[1] = 0,
        cut_list[1][1] = cuts_list_list[1][1].position_list[1],
        cut_list[1][2] = cuts_list_list[1][1].position_list[2],
        cut_list[1][3] = cuts_list_list[1][1].position_list[3],
        (cut_list[1][1] = BEAM_SKIP_START),
        (cut_list[1][((MAX_N_CUTS_PER_BOARD - 1) + 1)] = (board_list[1][1].length - BEAM_SKIP_END)),
        curved_intervals_board[1][1].start = board_list[1][1].curved_intervals[1].start,
        curved_intervals_board[1][1].end = board_list[1][1].curved_intervals[1].end,
        ((curved_intervals_board[1][1].start < curved_intervals_board[1][1].end) -> (((curved_intervals_board[1][1].start <= cut_list[1][1]) /\ (cut_list[1][1] <= curved_intervals_board[1][1].end)) \/ ((curved_intervals_board[1][1].start <= cut_list[1][2]) /\ (cut_list[1][2] <= curved_intervals_board[1][1].end)) \/ ((curved_intervals_board[1][1].start <= cut_list[1][3]) /\ (cut_list[1][3] <= curved_intervals_board[1][1].end)))),
        piece_length[1] = (cut_list[1][2] - cut_list[1][((1 - 1) + 1)]),
        (piece_length[1] >= 0),
        ((piece_length[1] = 0) -> (cut_list[1][2] = (board_list[1][1].length - BEAM_SKIP_END))),
        bad_intervals_board[1][1].start = board_list[1][1].bad_intervals[1].start,
        bad_intervals_board[1][1].end = board_list[1][1].bad_intervals[1].end,
        ((((bad_intervals_board[1][1].start >= cut_list[1][2]) \/ (cut_list[1][((1 - 1) + 1)] >= bad_intervals_board[1][1].end))) -> quality[2] = 1),
        ((not (((bad_intervals_board[1][1].start >= cut_list[1][2]) \/ (cut_list[1][((1 - 1) + 1)] >= bad_intervals_board[1][1].end)))) -> quality[2] = 0),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 1) -> pieces[2][1].quality = pieces[1][1].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 1) -> pieces[2][1].length = pieces[1][1].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 2) -> pieces[2][2].quality = pieces[1][2].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 2) -> pieces[2][2].length = pieces[1][2].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 3) -> pieces[2][3].quality = pieces[1][3].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 3) -> pieces[2][3].length = pieces[1][3].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 4) -> pieces[2][4].quality = pieces[1][4].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 4) -> pieces[2][4].length = pieces[1][4].length),
        pieces[2][(((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1)].length = (quality: quality[2], length: piece_length[1]).length,
        pieces[2][(((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1)].quality = (quality: quality[2], length: piece_length[1]).quality,
        piece_length[2] = (cut_list[1][3] - cut_list[1][((2 - 1) + 1)]),
        (piece_length[2] >= 0),
        ((piece_length[2] = 0) -> (cut_list[1][3] = (board_list[1][1].length - BEAM_SKIP_END))),
        bad_intervals_board[2][1].start = board_list[1][1].bad_intervals[1].start,
        bad_intervals_board[2][1].end = board_list[1][1].bad_intervals[1].end,
        ((((bad_intervals_board[2][1].start >= cut_list[1][3]) \/ (cut_list[1][((2 - 1) + 1)] >= bad_intervals_board[2][1].end))) -> quality[3] = 1),
        ((not (((bad_intervals_board[2][1].start >= cut_list[1][3]) \/ (cut_list[1][((2 - 1) + 1)] >= bad_intervals_board[2][1].end)))) -> quality[3] = 0),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 1) -> pieces[3][1].quality = pieces[2][1].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 1) -> pieces[3][1].length = pieces[2][1].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 2) -> pieces[3][2].quality = pieces[2][2].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 2) -> pieces[3][2].length = pieces[2][2].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 3) -> pieces[3][3].quality = pieces[2][3].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 3) -> pieces[3][3].length = pieces[2][3].length),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 4) -> pieces[3][4].quality = pieces[2][4].quality),
        (((((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 4) -> pieces[3][4].length = pieces[2][4].length),
        pieces[3][(((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1)].length = (quality: quality[3], length: piece_length[2]).length,
        pieces[3][(((0 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1)].quality = (quality: quality[3], length: piece_length[2]).quality,
        cut_list[2][1] = cuts_list_list[1][2].position_list[1],
        cut_list[2][2] = cuts_list_list[1][2].position_list[2],
        cut_list[2][3] = cuts_list_list[1][2].position_list[3],
        (cut_list[2][1] = BEAM_SKIP_START),
        (cut_list[2][((MAX_N_CUTS_PER_BOARD - 1) + 1)] = (board_list[1][2].length - BEAM_SKIP_END)),
        curved_intervals_board[2][1].start = board_list[1][2].curved_intervals[1].start,
        curved_intervals_board[2][1].end = board_list[1][2].curved_intervals[1].end,
        ((curved_intervals_board[2][1].start < curved_intervals_board[2][1].end) -> (((curved_intervals_board[2][1].start <= cut_list[2][1]) /\ (cut_list[2][1] <= curved_intervals_board[2][1].end)) \/ ((curved_intervals_board[2][1].start <= cut_list[2][2]) /\ (cut_list[2][2] <= curved_intervals_board[2][1].end)) \/ ((curved_intervals_board[2][1].start <= cut_list[2][3]) /\ (cut_list[2][3] <= curved_intervals_board[2][1].end)))),
        piece_length[3] = (cut_list[2][2] - cut_list[2][((1 - 1) + 1)]),
        (piece_length[3] >= 0),
        ((piece_length[3] = 0) -> (cut_list[2][2] = (board_list[1][2].length - BEAM_SKIP_END))),
        bad_intervals_board[3][1].start = board_list[1][2].bad_intervals[1].start,
        bad_intervals_board[3][1].end = board_list[1][2].bad_intervals[1].end,
        ((((bad_intervals_board[3][1].start >= cut_list[2][2]) \/ (cut_list[2][((1 - 1) + 1)] >= bad_intervals_board[3][1].end))) -> quality[4] = 1),
        ((not (((bad_intervals_board[3][1].start >= cut_list[2][2]) \/ (cut_list[2][((1 - 1) + 1)] >= bad_intervals_board[3][1].end)))) -> quality[4] = 0),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 1) -> pieces[4][1].length = pieces[3][1].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 1) -> pieces[4][1].quality = pieces[3][1].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 2) -> pieces[4][2].length = pieces[3][2].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 2) -> pieces[4][2].quality = pieces[3][2].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 3) -> pieces[4][3].length = pieces[3][3].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 3) -> pieces[4][3].quality = pieces[3][3].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 4) -> pieces[4][4].length = pieces[3][4].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1) != 4) -> pieces[4][4].quality = pieces[3][4].quality),
        pieces[4][(((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1)].length = (quality: quality[4], length: piece_length[3]).length,
        pieces[4][(((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (1 - 1)) + 1)].quality = (quality: quality[4], length: piece_length[3]).quality,
        piece_length[4] = (cut_list[2][3] - cut_list[2][((2 - 1) + 1)]),
        (piece_length[4] >= 0),
        ((piece_length[4] = 0) -> (cut_list[2][3] = (board_list[1][2].length - BEAM_SKIP_END))),
        bad_intervals_board[4][1].start = board_list[1][2].bad_intervals[1].start,
        bad_intervals_board[4][1].end = board_list[1][2].bad_intervals[1].end,
        ((((bad_intervals_board[4][1].start >= cut_list[2][3]) \/ (cut_list[2][((2 - 1) + 1)] >= bad_intervals_board[4][1].end))) -> quality[5] = 1),
        ((not (((bad_intervals_board[4][1].start >= cut_list[2][3]) \/ (cut_list[2][((2 - 1) + 1)] >= bad_intervals_board[4][1].end)))) -> quality[5] = 0),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 1) -> pieces[5][1].length = pieces[4][1].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 1) -> pieces[5][1].quality = pieces[4][1].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 2) -> pieces[5][2].length = pieces[4][2].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 2) -> pieces[5][2].quality = pieces[4][2].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 3) -> pieces[5][3].length = pieces[4][3].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 3) -> pieces[5][3].quality = pieces[4][3].quality),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 4) -> pieces[5][4].length = pieces[4][4].length),
        (((((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1) != 4) -> pieces[5][4].quality = pieces[4][4].quality),
        pieces[5][(((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1)].length = (quality: quality[5], length: piece_length[4]).length,
        pieces[5][(((1 * (MAX_N_CUTS_PER_BOARD - 1)) + (2 - 1)) + 1)].quality = (quality: quality[5], length: piece_length[4]).quality,
        forall(i in 1..4)(output_1[i] = pieces[5][i])
    ]);
predicate filtering_machine(array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): input_1, array[1..4] of var bool: input_2, var 0..(MAX_BOARD_LENGTH * N_BOARDS): input_3, array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): output_1, var 0..(MAX_BOARD_LENGTH * N_BOARDS): output_2, array[1..5] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): filtered_list, array[1..1] of array[1..4] of var bool: keep_decisions, array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): list_to_filter, array[1..5] of var 0..(MAX_BOARD_LENGTH * N_BOARDS): objective) =
    forall([
        list_to_filter[1][1].length = input_1[1].length,
        list_to_filter[1][1].quality = input_1[1].quality,
        list_to_filter[1][2].length = input_1[2].length,
        list_to_filter[1][2].quality = input_1[2].quality,
        list_to_filter[1][3].length = input_1[3].length,
        list_to_filter[1][3].quality = input_1[3].quality,
        list_to_filter[1][4].length = input_1[4].length,
        list_to_filter[1][4].quality = input_1[4].quality,
        keep_decisions[1][1] = input_2[1],
        keep_decisions[1][2] = input_2[2],
        keep_decisions[1][3] = input_2[3],
        keep_decisions[1][4] = input_2[4],
        objective[1] = input_3,
        (keep_decisions[1][1] -> (list_to_filter[1][1].quality = 1)),
        (keep_decisions[1][1] -> filtered_list[2][2].length = filtered_list[1][2].length),
        (keep_decisions[1][1] -> filtered_list[2][2].quality = filtered_list[1][2].quality),
        (keep_decisions[1][1] -> filtered_list[2][3].length = filtered_list[1][3].length),
        (keep_decisions[1][1] -> filtered_list[2][3].quality = filtered_list[1][3].quality),
        (keep_decisions[1][1] -> filtered_list[2][4].length = filtered_list[1][4].length),
        (keep_decisions[1][1] -> filtered_list[2][4].quality = filtered_list[1][4].quality),
        (keep_decisions[1][1] -> filtered_list[2][1].length = list_to_filter[1][1].length),
        (keep_decisions[1][1] -> filtered_list[2][1].quality = list_to_filter[1][1].quality),
        (keep_decisions[1][1] -> objective[2] = objective[1]),
        ((list_to_filter[1][1].quality = 1) /\ (not keep_decisions[1][1]) -> objective[2] = (objective[1] + list_to_filter[1][1].length)),
        ((not (list_to_filter[1][1].quality = 1)) /\ (not keep_decisions[1][1]) -> objective[2] = objective[1]),
        ((not keep_decisions[1][1]) -> filtered_list[2][2].quality = filtered_list[1][2].quality),
        ((not keep_decisions[1][1]) -> filtered_list[2][2].length = filtered_list[1][2].length),
        ((not keep_decisions[1][1]) -> filtered_list[2][3].quality = filtered_list[1][3].quality),
        ((not keep_decisions[1][1]) -> filtered_list[2][3].length = filtered_list[1][3].length),
        ((not keep_decisions[1][1]) -> filtered_list[2][4].quality = filtered_list[1][4].quality),
        ((not keep_decisions[1][1]) -> filtered_list[2][4].length = filtered_list[1][4].length),
        ((not keep_decisions[1][1]) -> filtered_list[2][1].length = (quality: 1, length: 0).length),
        ((not keep_decisions[1][1]) -> filtered_list[2][1].quality = (quality: 1, length: 0).quality),
        (keep_decisions[1][2] -> (list_to_filter[1][2].quality = 1)),
        (keep_decisions[1][2] -> filtered_list[3][1].quality = filtered_list[2][1].quality),
        (keep_decisions[1][2] -> filtered_list[3][1].length = filtered_list[2][1].length),
        (keep_decisions[1][2] -> filtered_list[3][3].quality = filtered_list[2][3].quality),
        (keep_decisions[1][2] -> filtered_list[3][3].length = filtered_list[2][3].length),
        (keep_decisions[1][2] -> filtered_list[3][4].quality = filtered_list[2][4].quality),
        (keep_decisions[1][2] -> filtered_list[3][4].length = filtered_list[2][4].length),
        (keep_decisions[1][2] -> filtered_list[3][2].length = list_to_filter[1][2].length),
        (keep_decisions[1][2] -> filtered_list[3][2].quality = list_to_filter[1][2].quality),
        (keep_decisions[1][2] -> objective[3] = objective[2]),
        ((list_to_filter[1][2].quality = 1) /\ (not keep_decisions[1][2]) -> objective[3] = (objective[2] + list_to_filter[1][2].length)),
        ((not (list_to_filter[1][2].quality = 1)) /\ (not keep_decisions[1][2]) -> objective[3] = objective[2]),
        ((not keep_decisions[1][2]) -> filtered_list[3][1].length = filtered_list[2][1].length),
        ((not keep_decisions[1][2]) -> filtered_list[3][1].quality = filtered_list[2][1].quality),
        ((not keep_decisions[1][2]) -> filtered_list[3][3].length = filtered_list[2][3].length),
        ((not keep_decisions[1][2]) -> filtered_list[3][3].quality = filtered_list[2][3].quality),
        ((not keep_decisions[1][2]) -> filtered_list[3][4].length = filtered_list[2][4].length),
        ((not keep_decisions[1][2]) -> filtered_list[3][4].quality = filtered_list[2][4].quality),
        ((not keep_decisions[1][2]) -> filtered_list[3][2].length = (quality: 1, length: 0).length),
        ((not keep_decisions[1][2]) -> filtered_list[3][2].quality = (quality: 1, length: 0).quality),
        (keep_decisions[1][3] -> (list_to_filter[1][3].quality = 1)),
        (keep_decisions[1][3] -> filtered_list[4][1].length = filtered_list[3][1].length),
        (keep_decisions[1][3] -> filtered_list[4][1].quality = filtered_list[3][1].quality),
        (keep_decisions[1][3] -> filtered_list[4][2].length = filtered_list[3][2].length),
        (keep_decisions[1][3] -> filtered_list[4][2].quality = filtered_list[3][2].quality),
        (keep_decisions[1][3] -> filtered_list[4][4].length = filtered_list[3][4].length),
        (keep_decisions[1][3] -> filtered_list[4][4].quality = filtered_list[3][4].quality),
        (keep_decisions[1][3] -> filtered_list[4][3].length = list_to_filter[1][3].length),
        (keep_decisions[1][3] -> filtered_list[4][3].quality = list_to_filter[1][3].quality),
        (keep_decisions[1][3] -> objective[4] = objective[3]),
        ((list_to_filter[1][3].quality = 1) /\ (not keep_decisions[1][3]) -> objective[4] = (objective[3] + list_to_filter[1][3].length)),
        ((not (list_to_filter[1][3].quality = 1)) /\ (not keep_decisions[1][3]) -> objective[4] = objective[3]),
        ((not keep_decisions[1][3]) -> filtered_list[4][1].quality = filtered_list[3][1].quality),
        ((not keep_decisions[1][3]) -> filtered_list[4][1].length = filtered_list[3][1].length),
        ((not keep_decisions[1][3]) -> filtered_list[4][2].quality = filtered_list[3][2].quality),
        ((not keep_decisions[1][3]) -> filtered_list[4][2].length = filtered_list[3][2].length),
        ((not keep_decisions[1][3]) -> filtered_list[4][4].quality = filtered_list[3][4].quality),
        ((not keep_decisions[1][3]) -> filtered_list[4][4].length = filtered_list[3][4].length),
        ((not keep_decisions[1][3]) -> filtered_list[4][3].length = (quality: 1, length: 0).length),
        ((not keep_decisions[1][3]) -> filtered_list[4][3].quality = (quality: 1, length: 0).quality),
        (keep_decisions[1][4] -> (list_to_filter[1][4].quality = 1)),
        (keep_decisions[1][4] -> filtered_list[5][1].quality = filtered_list[4][1].quality),
        (keep_decisions[1][4] -> filtered_list[5][1].length = filtered_list[4][1].length),
        (keep_decisions[1][4] -> filtered_list[5][2].quality = filtered_list[4][2].quality),
        (keep_decisions[1][4] -> filtered_list[5][2].length = filtered_list[4][2].length),
        (keep_decisions[1][4] -> filtered_list[5][3].quality = filtered_list[4][3].quality),
        (keep_decisions[1][4] -> filtered_list[5][3].length = filtered_list[4][3].length),
        (keep_decisions[1][4] -> filtered_list[5][4].length = list_to_filter[1][4].length),
        (keep_decisions[1][4] -> filtered_list[5][4].quality = list_to_filter[1][4].quality),
        (keep_decisions[1][4] -> objective[5] = objective[4]),
        ((list_to_filter[1][4].quality = 1) /\ (not keep_decisions[1][4]) -> objective[5] = (objective[4] + list_to_filter[1][4].length)),
        ((not (list_to_filter[1][4].quality = 1)) /\ (not keep_decisions[1][4]) -> objective[5] = objective[4]),
        ((not keep_decisions[1][4]) -> filtered_list[5][1].length = filtered_list[4][1].length),
        ((not keep_decisions[1][4]) -> filtered_list[5][1].quality = filtered_list[4][1].quality),
        ((not keep_decisions[1][4]) -> filtered_list[5][2].length = filtered_list[4][2].length),
        ((not keep_decisions[1][4]) -> filtered_list[5][2].quality = filtered_list[4][2].quality),
        ((not keep_decisions[1][4]) -> filtered_list[5][3].length = filtered_list[4][3].length),
        ((not keep_decisions[1][4]) -> filtered_list[5][3].quality = filtered_list[4][3].quality),
        ((not keep_decisions[1][4]) -> filtered_list[5][4].length = (quality: 1, length: 0).length),
        ((not keep_decisions[1][4]) -> filtered_list[5][4].quality = (quality: 1, length: 0).quality),
        forall(i in 1..4)(output_1[i] = filtered_list[5][i]),
        output_2 = objective[5]
    ]);
predicate reordering_piece_machine(array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): input_1, array[1..3] of var bool: input_2, array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): output_1, array[1..4] of var 0..2: held, array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): held_piece, array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): list_to_reorder, array[1..6] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): new_list, array[1..1] of array[1..3] of var bool: swapping_decisions, array[1..6] of var 0..N_PIECES: write_index) =
    forall([
        list_to_reorder[1][1].length = input_1[1].length,
        list_to_reorder[1][1].quality = input_1[1].quality,
        list_to_reorder[1][2].length = input_1[2].length,
        list_to_reorder[1][2].quality = input_1[2].quality,
        list_to_reorder[1][3].length = input_1[3].length,
        list_to_reorder[1][3].quality = input_1[3].quality,
        list_to_reorder[1][4].length = input_1[4].length,
        list_to_reorder[1][4].quality = input_1[4].quality,
        swapping_decisions[1][1] = input_2[1],
        swapping_decisions[1][2] = input_2[2],
        swapping_decisions[1][3] = input_2[3],
        held[1] = 0,
        held_piece[1].length = (quality: 1, length: 0).length,
        held_piece[1].quality = (quality: 1, length: 0).quality,
        write_index[1] = 0,
        (((held[1] = 0) /\ swapping_decisions[1][1]) -> held[2] = 1),
        (((held[1] = 0) /\ swapping_decisions[1][1]) -> held_piece[2].length = list_to_reorder[1][1].length),
        (((held[1] = 0) /\ swapping_decisions[1][1]) -> held_piece[2].quality = list_to_reorder[1][1].quality),
        (((held[1] = 0) /\ swapping_decisions[1][1]) -> new_list[2] = new_list[1]),
        (((held[1] = 0) /\ swapping_decisions[1][1]) -> write_index[2] = write_index[1]),
        (((write_index[1] + 1) != 1) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][1].length = new_list[1][1].length),
        (((write_index[1] + 1) != 1) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][1].quality = new_list[1][1].quality),
        (((write_index[1] + 1) != 2) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][2].length = new_list[1][2].length),
        (((write_index[1] + 1) != 2) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][2].quality = new_list[1][2].quality),
        (((write_index[1] + 1) != 3) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][3].length = new_list[1][3].length),
        (((write_index[1] + 1) != 3) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][3].quality = new_list[1][3].quality),
        (((write_index[1] + 1) != 4) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][4].length = new_list[1][4].length),
        (((write_index[1] + 1) != 4) /\ (not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][4].quality = new_list[1][4].quality),
        ((not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][(write_index[1] + 1)].length = list_to_reorder[1][1].length),
        ((not ((held[1] = 0) /\ swapping_decisions[1][1])) -> new_list[2][(write_index[1] + 1)].quality = list_to_reorder[1][1].quality),
        ((not ((held[1] = 0) /\ swapping_decisions[1][1])) -> write_index[2] = (write_index[1] + 1)),
        ((not ((held[1] = 0) /\ swapping_decisions[1][1])) -> held[2] = held[1]),
        ((not ((held[1] = 0) /\ swapping_decisions[1][1])) -> held_piece[2] = held_piece[1]),
        (((held[2] = 0) /\ swapping_decisions[1][2]) -> held[3] = 1),
        (((held[2] = 0) /\ swapping_decisions[1][2]) -> held_piece[3].length = list_to_reorder[1][2].length),
        (((held[2] = 0) /\ swapping_decisions[1][2]) -> held_piece[3].quality = list_to_reorder[1][2].quality),
        (((held[2] = 0) /\ swapping_decisions[1][2]) -> new_list[3] = new_list[2]),
        (((held[2] = 0) /\ swapping_decisions[1][2]) -> write_index[3] = write_index[2]),
        (((write_index[2] + 1) != 1) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][1].quality = new_list[2][1].quality),
        (((write_index[2] + 1) != 1) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][1].length = new_list[2][1].length),
        (((write_index[2] + 1) != 2) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][2].quality = new_list[2][2].quality),
        (((write_index[2] + 1) != 2) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][2].length = new_list[2][2].length),
        (((write_index[2] + 1) != 3) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][3].quality = new_list[2][3].quality),
        (((write_index[2] + 1) != 3) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][3].length = new_list[2][3].length),
        (((write_index[2] + 1) != 4) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][4].quality = new_list[2][4].quality),
        (((write_index[2] + 1) != 4) /\ (not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][4].length = new_list[2][4].length),
        ((not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][(write_index[2] + 1)].length = list_to_reorder[1][2].length),
        ((not ((held[2] = 0) /\ swapping_decisions[1][2])) -> new_list[3][(write_index[2] + 1)].quality = list_to_reorder[1][2].quality),
        ((not ((held[2] = 0) /\ swapping_decisions[1][2])) -> write_index[3] = (write_index[2] + 1)),
        ((not ((held[2] = 0) /\ swapping_decisions[1][2])) -> held[3] = held[2]),
        ((not ((held[2] = 0) /\ swapping_decisions[1][2])) -> held_piece[3] = held_piece[2]),
        (((held[3] = 0) /\ swapping_decisions[1][3]) -> held[4] = 1),
        (((held[3] = 0) /\ swapping_decisions[1][3]) -> held_piece[4].length = list_to_reorder[1][3].length),
        (((held[3] = 0) /\ swapping_decisions[1][3]) -> held_piece[4].quality = list_to_reorder[1][3].quality),
        (((held[3] = 0) /\ swapping_decisions[1][3]) -> new_list[4] = new_list[3]),
        (((held[3] = 0) /\ swapping_decisions[1][3]) -> write_index[4] = write_index[3]),
        (((write_index[3] + 1) != 1) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][1].length = new_list[3][1].length),
        (((write_index[3] + 1) != 1) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][1].quality = new_list[3][1].quality),
        (((write_index[3] + 1) != 2) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][2].length = new_list[3][2].length),
        (((write_index[3] + 1) != 2) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][2].quality = new_list[3][2].quality),
        (((write_index[3] + 1) != 3) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][3].length = new_list[3][3].length),
        (((write_index[3] + 1) != 3) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][3].quality = new_list[3][3].quality),
        (((write_index[3] + 1) != 4) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][4].length = new_list[3][4].length),
        (((write_index[3] + 1) != 4) /\ (not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][4].quality = new_list[3][4].quality),
        ((not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][(write_index[3] + 1)].length = list_to_reorder[1][3].length),
        ((not ((held[3] = 0) /\ swapping_decisions[1][3])) -> new_list[4][(write_index[3] + 1)].quality = list_to_reorder[1][3].quality),
        ((not ((held[3] = 0) /\ swapping_decisions[1][3])) -> write_index[4] = (write_index[3] + 1)),
        ((not ((held[3] = 0) /\ swapping_decisions[1][3])) -> held[4] = held[3]),
        ((not ((held[3] = 0) /\ swapping_decisions[1][3])) -> held_piece[4] = held_piece[3]),
        (((write_index[4] + 1) != 1) /\ (held[4] = 1) -> new_list[5][1].quality = new_list[4][1].quality),
        (((write_index[4] + 1) != 1) /\ (held[4] = 1) -> new_list[5][1].length = new_list[4][1].length),
        (((write_index[4] + 1) != 2) /\ (held[4] = 1) -> new_list[5][2].quality = new_list[4][2].quality),
        (((write_index[4] + 1) != 2) /\ (held[4] = 1) -> new_list[5][2].length = new_list[4][2].length),
        (((write_index[4] + 1) != 3) /\ (held[4] = 1) -> new_list[5][3].quality = new_list[4][3].quality),
        (((write_index[4] + 1) != 3) /\ (held[4] = 1) -> new_list[5][3].length = new_list[4][3].length),
        (((write_index[4] + 1) != 4) /\ (held[4] = 1) -> new_list[5][4].quality = new_list[4][4].quality),
        (((write_index[4] + 1) != 4) /\ (held[4] = 1) -> new_list[5][4].length = new_list[4][4].length),
        ((held[4] = 1) -> new_list[5][(write_index[4] + 1)].length = list_to_reorder[1][((N_PIECES - 1) + 1)].length),
        ((held[4] = 1) -> new_list[5][(write_index[4] + 1)].quality = list_to_reorder[1][((N_PIECES - 1) + 1)].quality),
        ((held[4] = 1) -> write_index[5] = (write_index[4] + 1)),
        (((write_index[5] + 1) != 1) /\ (held[4] = 1) -> new_list[6][1].quality = new_list[5][1].quality),
        (((write_index[5] + 1) != 1) /\ (held[4] = 1) -> new_list[6][1].length = new_list[5][1].length),
        (((write_index[5] + 1) != 2) /\ (held[4] = 1) -> new_list[6][2].quality = new_list[5][2].quality),
        (((write_index[5] + 1) != 2) /\ (held[4] = 1) -> new_list[6][2].length = new_list[5][2].length),
        (((write_index[5] + 1) != 3) /\ (held[4] = 1) -> new_list[6][3].quality = new_list[5][3].quality),
        (((write_index[5] + 1) != 3) /\ (held[4] = 1) -> new_list[6][3].length = new_list[5][3].length),
        (((write_index[5] + 1) != 4) /\ (held[4] = 1) -> new_list[6][4].quality = new_list[5][4].quality),
        (((write_index[5] + 1) != 4) /\ (held[4] = 1) -> new_list[6][4].length = new_list[5][4].length),
        ((held[4] = 1) -> new_list[6][(write_index[5] + 1)].length = held_piece[4].length),
        ((held[4] = 1) -> new_list[6][(write_index[5] + 1)].quality = held_piece[4].quality),
        ((held[4] = 1) -> write_index[6] = (write_index[5] + 1)),
        (((write_index[4] + 1) != 1) /\ (not (held[4] = 1)) -> new_list[5][1].quality = new_list[4][1].quality),
        (((write_index[4] + 1) != 1) /\ (not (held[4] = 1)) -> new_list[5][1].length = new_list[4][1].length),
        (((write_index[4] + 1) != 2) /\ (not (held[4] = 1)) -> new_list[5][2].quality = new_list[4][2].quality),
        (((write_index[4] + 1) != 2) /\ (not (held[4] = 1)) -> new_list[5][2].length = new_list[4][2].length),
        (((write_index[4] + 1) != 3) /\ (not (held[4] = 1)) -> new_list[5][3].quality = new_list[4][3].quality),
        (((write_index[4] + 1) != 3) /\ (not (held[4] = 1)) -> new_list[5][3].length = new_list[4][3].length),
        (((write_index[4] + 1) != 4) /\ (not (held[4] = 1)) -> new_list[5][4].quality = new_list[4][4].quality),
        (((write_index[4] + 1) != 4) /\ (not (held[4] = 1)) -> new_list[5][4].length = new_list[4][4].length),
        ((not (held[4] = 1)) -> new_list[5][(write_index[4] + 1)].length = list_to_reorder[1][((N_PIECES - 1) + 1)].length),
        ((not (held[4] = 1)) -> new_list[5][(write_index[4] + 1)].quality = list_to_reorder[1][((N_PIECES - 1) + 1)].quality),
        ((not (held[4] = 1)) -> write_index[5] = (write_index[4] + 1)),
        ((not (held[4] = 1)) -> new_list[6] = new_list[5]),
        ((not (held[4] = 1)) -> write_index[6] = write_index[5]),
        forall(i in 1..4)(output_1[i] = new_list[6][i])
    ]);
int: N_BOARDS = 2;
int: N_BEAMS = 1;
int: MAX_BOARD_LENGTH = 770;
int: MAX_N_INTERVALS = 1;
int: MAX_N_CUTS_PER_BOARD = 3;
int: N_PIECES = 4;
int: BEAM_LENGTH = 500;
int: BEAM_DEPTH = 2;
int: MAX_PIECES_PER_BEAM = 2;
int: MIN_DIST_BETWEEN_PIECES = 1;
int: BEAM_SKIP_START = 10;
int: BEAM_SKIP_END = 10;
int: MIN_LENGTH_OF_BOARD_IN_LAYER = 10;
int: GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS = 10;
int: MAX_SHIFT_CURVED_CUT = 50;
array[1..4] of array[1..2] of int: FORBIDDEN_INTERVALS = [[90, 110], [190, 210], [290, 310], [390, 410]];
array[1..2] of Board: GIVEN_INITIAL_BOARDS = [(
        length: 770,
        bad_intervals: [(
        start: 0,
        end: 0
    )],
        curved_intervals: [(
        start: 0,
        end: 0
    )]
    ), (
        length: 270,
        bad_intervals: [(
        start: 0,
        end: 0
    )],
        curved_intervals: [(
        start: 0,
        end: 0
    )]
    )];
array[1..1] of array[1..2] of record(
    var 0..MAX_BOARD_LENGTH: length,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals
): initial_boards;
array[1..1] of array[1..2] of record(
    array[1..3] of var 0..MAX_BOARD_LENGTH: position_list
): cuts_list_list;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): pieces;
array[1..4] of array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals_board__cutting_machine__1;
array[1..1] of array[1..2] of record(
    var 0..MAX_BOARD_LENGTH: length,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): bad_intervals,
    array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals
): board_list__cutting_machine__1;
array[1..2] of array[1..1] of record(
    var 0..MAX_BOARD_LENGTH: start,
    var 0..MAX_BOARD_LENGTH: end
): curved_intervals_board__cutting_machine__1;
array[1..2] of array[1..3] of var 0..MAX_BOARD_LENGTH: cut_list__cutting_machine__1;
array[1..1] of array[1..2] of record(
    array[1..3] of var 0..MAX_BOARD_LENGTH: position_list
): cuts_list_list__cutting_machine__1;
array[1..4] of var int: piece_length__cutting_machine__1;
array[1..5] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): pieces__cutting_machine__1;
array[1..5] of var 0..1: quality__cutting_machine__1;
array[1..2] of var 0..(MAX_BOARD_LENGTH * N_BOARDS): objective;
array[1..1] of array[1..4] of var bool: keep_decisions;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): filtered_pieces;
array[1..5] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): filtered_list__filtering_machine__1;
array[1..1] of array[1..4] of var bool: keep_decisions__filtering_machine__1;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): list_to_filter__filtering_machine__1;
array[1..5] of var 0..(MAX_BOARD_LENGTH * N_BOARDS): objective__filtering_machine__1;
array[1..1] of array[1..3] of var bool: swapping_decisions;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): reordered_pieces;
array[1..4] of var 0..2: held__reordering_piece_machine__1;
array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): held_piece__reordering_piece_machine__1;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): list_to_reorder__reordering_piece_machine__1;
array[1..6] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): new_list__reordering_piece_machine__1;
array[1..1] of array[1..3] of var bool: swapping_decisions__reordering_piece_machine__1;
array[1..6] of var 0..N_PIECES: write_index__reordering_piece_machine__1;
array[1..5] of var int: current_index__checking_machine__1;
array[1..9] of var int: depth__checking_machine__1;
array[1..5] of array[1..4] of var 0..BEAM_LENGTH: layer_lengths__checking_machine__1;
array[1..9] of var int: length__checking_machine__1;
array[1..9] of var int: n_length__checking_machine__1;
array[1..5] of var int: n_prev_layer__checking_machine__1;
array[1..5] of var int: new_beam__checking_machine__1;
array[1..1] of array[1..4] of record(
    var 0..MAX_BOARD_LENGTH: length,
    var 0..1: quality
): pieces__checking_machine__1;
array[1..17] of array[1..4] of var 0..BEAM_LENGTH: prev_layer_lengths__checking_machine__1;
array[1..16] of var int: s__checking_machine__1;
array[1..5] of var int: total_depth__checking_machine__1;
constraint initial_boards[1][1].length = GIVEN_INITIAL_BOARDS[1].length;
constraint initial_boards[1][1].bad_intervals[1].start = GIVEN_INITIAL_BOARDS[1].bad_intervals[1].start;
constraint initial_boards[1][1].bad_intervals[1].end = GIVEN_INITIAL_BOARDS[1].bad_intervals[1].end;
constraint initial_boards[1][1].curved_intervals[1].start = GIVEN_INITIAL_BOARDS[1].curved_intervals[1].start;
constraint initial_boards[1][1].curved_intervals[1].end = GIVEN_INITIAL_BOARDS[1].curved_intervals[1].end;
constraint initial_boards[1][2].length = GIVEN_INITIAL_BOARDS[2].length;
constraint initial_boards[1][2].bad_intervals[1].start = GIVEN_INITIAL_BOARDS[2].bad_intervals[1].start;
constraint initial_boards[1][2].bad_intervals[1].end = GIVEN_INITIAL_BOARDS[2].bad_intervals[1].end;
constraint initial_boards[1][2].curved_intervals[1].start = GIVEN_INITIAL_BOARDS[2].curved_intervals[1].start;
constraint initial_boards[1][2].curved_intervals[1].end = GIVEN_INITIAL_BOARDS[2].curved_intervals[1].end;
constraint cutting_machine(initial_boards[1], cuts_list_list[1], pieces[1], bad_intervals_board__cutting_machine__1, board_list__cutting_machine__1, curved_intervals_board__cutting_machine__1, cut_list__cutting_machine__1, cuts_list_list__cutting_machine__1, piece_length__cutting_machine__1, pieces__cutting_machine__1, quality__cutting_machine__1);
constraint objective[1] = 0;
constraint filtering_machine(pieces[1], keep_decisions[1], objective[1], filtered_pieces[1], objective[2], filtered_list__filtering_machine__1, keep_decisions__filtering_machine__1, list_to_filter__filtering_machine__1, objective__filtering_machine__1);
constraint reordering_piece_machine(filtered_pieces[1], swapping_decisions[1], reordered_pieces[1], held__reordering_piece_machine__1, held_piece__reordering_piece_machine__1, list_to_reorder__reordering_piece_machine__1, new_list__reordering_piece_machine__1, swapping_decisions__reordering_piece_machine__1, write_index__reordering_piece_machine__1);
constraint checking_machine(reordered_pieces[1], current_index__checking_machine__1, depth__checking_machine__1, layer_lengths__checking_machine__1, length__checking_machine__1, n_length__checking_machine__1, n_prev_layer__checking_machine__1, new_beam__checking_machine__1, pieces__checking_machine__1, prev_layer_lengths__checking_machine__1, s__checking_machine__1, total_depth__checking_machine__1);
solve minimize objective[2];