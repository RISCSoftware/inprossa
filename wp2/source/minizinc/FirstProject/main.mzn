
include "checking_machine.mzn";


array[1..40] of var float: original_lengths;
constraint layer_lengths[3] > 0.0;
constraint forall(i in 1..40)(
    original_lengths[i] < layer_length
  );
solve satisfy;

output [
  "Layer assignments:\n"
] ++
[
  if j = 1 then "\nLayer \(i): " else "" endif ++ show(layers[i,j]) ++ " "
  | i in 1..n_layers, j in 1..max_pieces_per_layer
];
