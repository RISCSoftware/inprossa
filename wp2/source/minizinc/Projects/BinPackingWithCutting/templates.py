import random


dsl_template = """
BOX_CAPACITIES : DSList({n_items}, DSInt()) = {box_capacities}
ITEM_LENGTHS : DSList({n_items}, DSInt()) = {item_lengths}
MAX_ITEM_LENGTH : int = {max_item_length}

NBOXES : int = {n_items}
NITEMS : int = {n_items}

assignments: DSList(NITEMS * 2, DSInt(1, NBOXES))
cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))

def cutting_machine(
    cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
    ):
    cutting_cost: DSInt(0, NITEMS) = 0
    cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
    for n_item in range(1, NITEMS + 1):
        cut_items[2 * n_item] = ITEM_LENGTHS[n_item] - cut_positions[n_item]
        cut_items[2 * n_item - 1] = cut_positions[n_item]
        if cut_positions[n_item] != 0:
            # A cut is made
            cutting_cost = cutting_cost + 1

    return cut_items, cutting_cost


def not_exceed(
    assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
    cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
    ):
    use_cost: DSInt(0, NITEMS * 3) = 0
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_LENGTHS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + cut_items[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            use_cost = use_cost + 3
    return use_cost

cutting_cost : DSInt(0, NITEMS)
cut_items, cutting_cost = cutting_machine(cut_positions)
use_cost: DSInt(0, NITEMS * 3) = 0
use_cost = not_exceed(assignments, cut_items)
total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
minimize(total_cost)
"""

dsl_template_2 = """
BOX_CAPACITIES : DSList({n_items}, DSInt()) = {box_capacities}
ITEM_LENGTHS : DSList({n_items}, DSInt()) = {item_lengths}
MAX_ITEM_LENGTH : int = {max_item_length}

NBOXES : int = {n_items}
NITEMS : int = {n_items}

Cut_item = DSInt(0, MAX_ITEM_LENGTH)

assignments: DSList(NITEMS * 2, DSInt(1, NBOXES))
cut_positions: DSList(NITEMS, Cut_item)
cut_items: DSList(NITEMS * 2, Cut_item)

def cutting_machine(
    cut_positions: DSList(NITEMS, Cut_item)
    ):
    cutting_cost: DSInt(0, NITEMS) = 0
    cut_items: DSList(NITEMS * 2, Cut_item)
    for n_item in range(1, NITEMS + 1):
        cut_items[2 * n_item] = ITEM_LENGTHS[n_item] - cut_positions[n_item]
        cut_items[2 * n_item - 1] = cut_positions[n_item]
        if cut_positions[n_item] != 0:
            # A cut is made
            cutting_cost = cutting_cost + 1

    return cut_items, cutting_cost


def not_exceed(
    assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
    cut_items: DSList(NITEMS * 2, Cut_item)
    ):
    use_cost: DSInt(0, NITEMS * 3) = 0
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_LENGTHS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + cut_items[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            use_cost = use_cost + 3
    return use_cost

cutting_cost : DSInt(0, NITEMS)
cut_items, cutting_cost = cutting_machine(cut_positions)
use_cost: DSInt(0, NITEMS * 3) = 0
use_cost = not_exceed(assignments, cut_items)
total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
minimize(total_cost)
"""

dsl_template_3 = """
BOX_CAPACITIES : DSList({n_items}, DSInt()) = {box_capacities}
ITEM_LENGTHS : DSList({n_items}, DSInt()) = {item_lengths}
MAX_ITEM_LENGTH : int = {max_item_length}

NBOXES : int = {n_items}
NITEMS : int = {n_items}

Cut_item = DSInt(0, MAX_ITEM_LENGTH)

assignments: DSList(NITEMS * 2, DSInt(1, NBOXES))
cut_positions: DSList(NITEMS, Cut_item)
cut_items: DSList(NITEMS * 2, Cut_item)

# Symmetry break: anchor one variable to reduce equivalent box permutations
assert assignments[1] == 1

def cutting_machine(
    cut_positions: DSList(NITEMS, Cut_item)
    ):
    cutting_cost: DSInt(0, NITEMS) = 0
    cut_items: DSList(NITEMS * 2, Cut_item)
    for n_item in range(1, NITEMS + 1):
        cut_items[2 * n_item] = ITEM_LENGTHS[n_item] - cut_positions[n_item]
        cut_items[2 * n_item - 1] = cut_positions[n_item]
        if cut_positions[n_item] != 0:
            # A cut is made
            cutting_cost = cutting_cost + 1

    return cut_items, cutting_cost


def not_exceed(
    assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
    cut_items: DSList(NITEMS * 2, Cut_item)
    ):
    use_cost: DSInt(0, NITEMS * 3) = 0
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_LENGTHS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS * 2 + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + cut_items[j]

        assert cap[i] <= BOX_CAPACITIES[i]
        if cap[i] > 0:
            use_cost = use_cost + 3

        # Symmetry break: boxes used must be a prefix 1..k (no gaps)
        if i < NBOXES - 1:
            if cap[i] == 0:
                assert cap[i + 1] == 0
    return use_cost

cutting_cost : DSInt(0, NITEMS)
cut_items, cutting_cost = cutting_machine(cut_positions)
use_cost: DSInt(0, NITEMS * 3) = 0
use_cost = not_exceed(assignments, cut_items)
total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
minimize(total_cost)
"""

# dsl_template_3 = """
# BOX_CAPACITIES : DSList({n_items}, DSInt()) = {box_capacities}
# ITEM_LENGTHS   : DSList({n_items}, DSInt()) = {item_lengths}

# MAX_ITEM_LENGTH  : int = {max_item_length}

# NBOXES : int = {n_items}
# NITEMS : int = {n_items}

# assignments  : DSList(NITEMS * 2, DSInt(1, NBOXES))
# cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))


# def cutting_machine(
#     cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
#     ):
#     cutting_cost: DSInt(0, NITEMS) = 0
#     cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))

#     for n_item in range(1, NITEMS + 1):

#         # Tighten: cut position must be within item length
#         assert cut_positions[n_item] <= ITEM_LENGTHS[n_item]

#         # Only allow real cuts: 0 (no cut) OR 1..ITEM_LENGTHS[n]-1
#         if cut_positions[n_item] != 0:
#             assert cut_positions[n_item] <= ITEM_LENGTHS[n_item] - 1

#         cut_items[2 * n_item]     = ITEM_LENGTHS[n_item] - cut_positions[n_item]
#         cut_items[2 * n_item - 1] = cut_positions[n_item]

#         if cut_positions[n_item] != 0:
#             cutting_cost = cutting_cost + 1
#         else:
#             # When no cut: piece (2*n_item-1) is always 0-length.
#             # Fix its assignment to kill symmetry.
#             assert assignments[2 * n_item - 1] == 1

#     return cut_items, cutting_cost


# def not_exceed(
#     assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
#     cut_items:   DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
#     ):
#     use_cost: DSInt(0, NITEMS * 3) = 0
#     cap: DSList(NBOXES, DSInt(0, sum(ITEM_LENGTHS)))

#     for i in range(1, NBOXES + 1):
#         cap[i] = 0
#         for j in range(1, NITEMS * 2 + 1):
#             if assignments[j] == i:
#                 cap[i] = cap[i] + cut_items[j]

#         assert cap[i] <= BOX_CAPACITIES[i]

#         if cap[i] > 0:
#             use_cost = use_cost + 3

#         # Symmetry break: boxes used must be a prefix 1..k (no gaps)
#         if i < NBOXES - 1:
#             if cap[i] == 0:
#                 assert cap[i + 1] == 0

#     return use_cost


# cutting_cost : DSInt(0, NITEMS)
# cut_items, cutting_cost = cutting_machine(cut_positions)

# use_cost: DSInt(0, NITEMS * 3) = 0
# use_cost = not_exceed(assignments, cut_items)

# total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
# minimize(total_cost)
# """
# dsl_template_4 = """
# BOX_CAPACITIES : DSList({n_items}, DSInt()) = {box_capacities}
# ITEM_LENGTHS   : DSList({n_items}, DSInt()) = {item_lengths}

# MAX_ITEM_LENGTH  : int = {max_item_length}
# TOTAL_LENGTH     : int = sum(ITEM_LENGTHS)

# NBOXES : int = {n_items}
# NITEMS : int = {n_items}

# assignments  : DSList(NITEMS * 2, DSInt(1, NBOXES))
# cut_positions: DSList(NITEMS,     DSInt(0, MAX_ITEM_LENGTH))

# # Symmetry break: anchor one variable to reduce equivalent box permutations
# assert assignments[1] == 1


# def cutting_machine(
#     cut_positions: DSList(NITEMS, DSInt(0, MAX_ITEM_LENGTH))
#     ):
#     cutting_cost: DSInt(0, NITEMS) = 0
#     cut_items: DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))

#     for n_item in range(1, NITEMS + 1):

#         # Tighten: cut position must be within item length
#         assert cut_positions[n_item] <= ITEM_LENGTHS[n_item]

#         # Only allow real cuts: 0 (no cut) OR 1..ITEM_LENGTHS[n]-1
#         if cut_positions[n_item] != 0:
#             assert cut_positions[n_item] <= ITEM_LENGTHS[n_item] - 1

#         cut_items[2 * n_item]     = ITEM_LENGTHS[n_item] - cut_positions[n_item]
#         cut_items[2 * n_item - 1] = cut_positions[n_item]

#         if cut_positions[n_item] != 0:
#             cutting_cost = cutting_cost + 1
#         else:
#             # When no cut: piece (2*n_item-1) is always 0-length.
#             # Fix its assignment to kill symmetry.
#             assert assignments[2 * n_item - 1] == 1

#     return cut_items, cutting_cost


# def not_exceed(
#     assignments: DSList(NITEMS * 2, DSInt(1, NBOXES)),
#     cut_items:   DSList(NITEMS * 2, DSInt(0, MAX_ITEM_LENGTH))
#     ):
#     use_cost: DSInt(0, NITEMS * 3) = 0
#     cap: DSList(NBOXES, DSInt(0, TOTAL_LENGTH))

#     for i in range(1, NBOXES + 1):
#         cap[i] = 0
#         for j in range(1, NITEMS * 2 + 1):
#             if assignments[j] == i:
#                 cap[i] = cap[i] + cut_items[j]

#         assert cap[i] <= BOX_CAPACITIES[i]

#         if cap[i] > 0:
#             use_cost = use_cost + 3

#         if i < NBOXES:
#             # Symmetry break 1: boxes used are a prefix (no gaps)
#             if cap[i] == 0:
#                 assert cap[i + 1] == 0

#             # Symmetry break 2 (all boxes identical): enforce non-increasing loads
#             assert cap[i] >= cap[i + 1]

#     assert sum(cap) == TOTAL_LENGTH
#     return use_cost


# cutting_cost : DSInt(0, NITEMS)
# cut_items, cutting_cost = cutting_machine(cut_positions)

# use_cost: DSInt(0, NITEMS * 3) = 0
# use_cost = not_exceed(assignments, cut_items)

# total_cost: DSInt(0, NITEMS * 4) = cutting_cost + use_cost
# minimize(total_cost)
# """


minizinc_template = """
% FILLED CONSTANTS / DATA 
int: NBOXES = {n_items};
int: NITEMS = {n_items};

array[1..NBOXES] of int: BOX_CAPACITIES = {box_capacities};
array[1..NITEMS] of int: ITEM_LENGTHS   = {item_lengths};

int: MAX_ITEM_LENGTH = max(i in 1..NITEMS)(ITEM_LENGTHS[i]);
int: TOTAL_LENGTH    = sum(i in 1..NITEMS)(ITEM_LENGTHS[i]);

% DECISION VARIABLES 
array[1..NITEMS] of var 0..MAX_ITEM_LENGTH: cut_positions;
array[1..2*NITEMS] of var 1..NBOXES: assignments;

% DERIVED VARIABLES 
array[1..2*NITEMS] of var 0..MAX_ITEM_LENGTH: cut_items;
array[1..NBOXES] of var 0..TOTAL_LENGTH: load;
array[1..NBOXES] of var bool: used;

% CUTTING MACHINE (cut_items + cutting_cost) 
constraint forall(i in 1..NITEMS) (
    cut_positions[i] <= ITEM_LENGTHS[i]
);

constraint forall(i in 1..NITEMS) (
    cut_items[2*i - 1] = cut_positions[i] /\\
    cut_items[2*i]     = ITEM_LENGTHS[i] - cut_positions[i]
);

var 0..NITEMS: cutting_cost =
    sum(i in 1..NITEMS)( cut_positions[i] != 0 );

% NOT_EXCEED (box loads + use_cost) 
constraint forall(b in 1..NBOXES) (
    load[b] = sum(j in 1..2*NITEMS)(
        cut_items[j] * (assignments[j] == b)
    )
);

constraint forall(b in 1..NBOXES) (
    load[b] <= BOX_CAPACITIES[b]
);

% used[b] <-> load[b] > 0
constraint forall(b in 1..NBOXES) (
    load[b] <= BOX_CAPACITIES[b] * used[b]
);

var 0..(3*NBOXES): use_cost =
    3 * sum(b in 1..NBOXES)( used[b] );

% OBJECTIVE 
int: MAX_TOTAL_COST = NITEMS + 3*NBOXES;
var 0..MAX_TOTAL_COST: total_cost = cutting_cost + use_cost;

solve minimize total_cost;
"""
minizinc_template_2 = """
int: NBOXES = {n_items};
int: NITEMS = {n_items};

array[1..NBOXES] of int: BOX_CAPACITIES = {box_capacities};
array[1..NITEMS] of int: ITEM_LENGTHS   = {item_lengths};

int: MAX_ITEM_LENGTH = max(ITEM_LENGTHS);
int: TOTAL_LENGTH    = sum(ITEM_LENGTHS);

% DECISION VARIABLES 
array[1..NITEMS] of var 0..MAX_ITEM_LENGTH: cut_positions;
array[1..2*NITEMS] of var 1..NBOXES: assignments;

% DERIVED VARIABLES 
array[1..2*NITEMS] of var 0..MAX_ITEM_LENGTH: cut_items;

% prefix loads: load[b,1] = 0 and load[b,j+1] is after processing item j
array[1..NBOXES, 1..2*NITEMS+1] of var 0..TOTAL_LENGTH: load;
array[1..NBOXES] of var bool: used;

% CUTTING MACHINE (cut_items + cutting_cost) 
constraint forall(i in 1..NITEMS) (
    cut_positions[i] <= ITEM_LENGTHS[i]
);

constraint forall(i in 1..NITEMS) (
    cut_items[2*i - 1] = cut_positions[i] /\\
    cut_items[2*i]     = ITEM_LENGTHS[i] - cut_positions[i]
);

% count nonzero cut positions
var 0..NITEMS: cutting_cost =
    sum(i in 1..NITEMS)(
        if cut_positions[i] != 0 then 1 else 0 endif
    );

 % LOADS 
constraint forall(b in 1..NBOXES) (
    load[b, 1] = 0
);

 % accumulate loads per box
constraint forall(b in 1..NBOXES, j in 1..2*NITEMS) (
    load[b, j+1] =
        load[b, j] + (if assignments[j] == b then cut_items[j] else 0 endif)
);

 % capacity
constraint forall(b in 1..NBOXES) (
    load[b, 2*NITEMS + 1] <= BOX_CAPACITIES[b]
);

 % used[b] <-> load_final[b] > 0
constraint forall(b in 1..NBOXES) (
    (used[b] -> load[b, 2*NITEMS + 1] >= 1) /\\
    (not used[b] -> load[b, 2*NITEMS + 1] = 0)
);

 % use cost = 3 per used box
var 0..(3*NBOXES): use_cost =
    3 * sum(b in 1..NBOXES)(
        if used[b] then 1 else 0 endif
    );

 % OBJECTIVE 
int: MAX_TOTAL_COST = NITEMS + 3*NBOXES;
var 0..MAX_TOTAL_COST: total_cost = cutting_cost + use_cost;

solve minimize total_cost;
"""

def fill_templates(n_items: int, box_capacities: list, item_lengths: list):
    codes = dict()
    max_item_length = max(item_lengths)

    codes["dsl_code"] = dsl_template.format(
        n_items=n_items,
        box_capacities=box_capacities,
        item_lengths=item_lengths,
        max_item_length=max_item_length
    )
    codes["dsl_code_2"] = dsl_template_2.format(
        n_items=n_items,
        box_capacities=box_capacities,
        item_lengths=item_lengths,
        max_item_length=max_item_length
    )
    codes["dsl_code_3"] = dsl_template_3.format(
        n_items=n_items,
        box_capacities=box_capacities,
        item_lengths=item_lengths,
        max_item_length=max_item_length,
    )
    # codes["dsl_code_4"] = dsl_template_4.format(
    #     n_items=n_items,
    #     box_capacities=box_capacities,
    #     item_lengths=item_lengths,
    #     max_item_length=max_item_length,
    # )
    codes["minizinc_code"] = minizinc_template.format(
        n_items=n_items,
        box_capacities=box_capacities,
        item_lengths=item_lengths
    )
    codes["minizinc_code_2"] = minizinc_template_2.format(
        n_items=n_items,
        box_capacities=box_capacities,
        item_lengths=item_lengths
    )
    return {
        "dsl":      [codes["dsl_code"],
                     codes["dsl_code_2"],
                     codes["dsl_code_3"],
                    #  codes["dsl_code_4"]
                    ],
        # "minizinc": [codes["minizinc_code"],
        #              codes["minizinc_code_2"]
        #             ]
        }


def create_bin_packing_codes(n_items: int, box_capacity: int = 10, random_seed=0) -> str:
    random.seed(random_seed)
    # super-simple capacities and lengths; tweak as needed
    box_capacities = [box_capacity] * n_items
    item_lengths = [random.randint(1, box_capacity) for _ in range(n_items)] 
    
    return fill_templates(n_items, box_capacities, item_lengths)