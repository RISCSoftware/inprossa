
include "constraints.mzn";

int: max_pieces_per_layer;
float: layer_length;
int: min_consecutive_distance;
array[1..40] of float: original_lengths;

int: n_pieces = length(original_lengths);
int: n_layers = ceil(n_pieces / max_pieces_per_layer);
int: total_slots = n_layers * max_pieces_per_layer;
int: n_padding_zeros = total_slots - n_pieces;

array[1..total_slots] of float: padded_pieces = 
  [ original_lengths[i] | i in 1..n_pieces ] ++ [ 0.0 | i in 1..n_padding_zeros ];

array[1..total_slots] of var 0.0..layer_length: piece_lengths;

array[1..n_layers, 1..max_pieces_per_layer] of var 0.0..layer_length: layers =
  array2d(1..n_layers, 1..max_pieces_per_layer, piece_lengths);

array[1..n_layers] of var 0.0..layer_length: layer_lengths;
array[1..n_layers, 1..max_pieces_per_layer] of var 0.0..layer_length: partial_sums;

solve satisfy;

output [
  "Layer assignments:\n"
] ++
[
  if j = 1 then "\nLayer \(i): " else "" endif ++ show(layers[i,j]) ++ " "
  | i in 1..n_layers, j in 1..max_pieces_per_layer
];
