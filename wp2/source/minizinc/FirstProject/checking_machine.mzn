include "predicates_checking_machine.mzn";

% Define the parameters
int: max_pieces_per_layer;
float: layer_length;
int: min_consecutive_distance;

% Calculate the number of pieces, layers...
int: n_pieces = length(original_lengths);
int: n_layers = ceil(n_pieces / max_pieces_per_layer);
int: total_slots = n_layers * max_pieces_per_layer;
int: n_padding_zeros = total_slots - n_pieces;

% Create an array to hold the padded pieces
array[1..total_slots] of float: padded_pieces = 
  [ original_lengths[i] | i in 1..n_pieces ] ++ [ 0.0 | i in 1..n_padding_zeros ];

% This ensures that piece_lengths is an array of variables
% TODO there might be a better way to do this (or may be not needed)
array[1..total_slots] of var 0.0..layer_length: piece_lengths;
constraint forall(i in 1..total_slots)(
  padded_pieces[i] = piece_lengths[i]
);

% Create a 2D array for layers
array[1..n_layers, 1..max_pieces_per_layer] of var 0.0..layer_length: layers =
  array2d(1..n_layers, 1..max_pieces_per_layer, piece_lengths);

% Create an array to hold the layer lengths and partial sums
array[1..n_layers] of var 0.0..layer_length: layer_lengths;
array[1..n_layers, 1..max_pieces_per_layer] of var 0.0..layer_length: partial_sums;

% Compute partial sums incrementally
constraint forall(l in 1..n_layers, s in 1..max_pieces_per_layer)(
  if s = 1 then partial_sums[l, s] = layers[l, s]
  else partial_sums[l, s] = partial_sums[l, s - 1] + layers[l, s]
  endif
);

% Compute length of each layer
constraint forall(l in 1..n_layers)(
  layer_lengths[l] = partial_sums[l, max_pieces_per_layer]
);

% Each layer must not exceed the max allowed length
constraint forall(l in 1..n_layers)(
  layer_lengths[l] <= layer_length
);

% If a layer is not full, the next layer must be empty
constraint forall(l in 1..n_layers - 1)(
  (layer_lengths[l] < layer_length) -> (layer_lengths[l + 1] = 0)
);

% Ensure no two partial sums in consecutive layers are too close
constraint forall(i in 1..n_layers - 1, j in 1..max_pieces_per_layer - 1, k in 1..max_pieces_per_layer - 1)(
  (partial_sums[i, j] > 0.0 /\ partial_sums[i + 1, k] > 0.0 /\
  partial_sums[i, j] < layer_length /\ partial_sums[i + 1, k] < layer_length) ->
  abs(partial_sums[i, j] - partial_sums[i + 1, k]) >= min_consecutive_distance
);

% Ensure partial sums are not in forbidden zones
constraint forall(i in 1..n_layers, j in 1..max_pieces_per_layer)(
  let { var float: cut_pos = sum(j_index in 1..j)(layers[i, j_index]) } in
    (cut_pos > 0.0 /\ cut_pos < layer_length) -> not_in_forbidden(cut_pos)
);
