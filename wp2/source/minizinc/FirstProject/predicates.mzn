int: n_forbidden_zones;
array[1..n_forbidden_zones, 1..2] of int: forbidden_zones;

predicate not_in_forbidden(var float: val) =
  forall(f in 1..n_forbidden_zones)(
    val < forbidden_zones[f, 1] \/ val > forbidden_zones[f, 2]
  );
