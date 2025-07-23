
include "checking_machine.mzn";


array[1..40] of float: original_lengths;

solve satisfy;

output [
  "Layer assignments:\n"
] ++
[
  if j = 1 then "\nLayer \(i): " else "" endif ++ show(layers[i,j]) ++ " "
  | i in 1..n_layers, j in 1..max_pieces_per_layer
];
