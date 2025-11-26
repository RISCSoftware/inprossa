from z3 import Int, Bool, If, Or, And, Optimize

# --- Problem data ---
W = 10    # bin width
H = 6     # bin height

items = [
    (4,3),
    (3,2),
    (5,3),
    (2,4),
    (3,3),
    (5,2)
]
n = len(items)

# We assume a maximum of m bins (an upper bound).
# In worst case one item per bin → m = n
m = n

# --- Variables ---
# For each item i: assign bin b_i in [0..m-1]
b = [ Int(f"b_{i}") for i in range(n) ]
# For each item i: x_i, y_i coordinates of the lower‐left in the bin
x = [ Int(f"x_{i}") for i in range(n) ]
y = [ Int(f"y_{i}") for i in range(n) ]

# For each bin j: whether it is used
u = [ Bool(f"u_{j}") for j in range(m) ]

opt = Optimize()

# --- Constraints ---
# Bin‐index domains
for i in range(n):
    opt.add( And(b[i] >= 0, b[i] < m) )

# If item i is assigned to bin j, then bin j is “used”
for i in range(n):
    for j in range(m):
        # If b[i] == j then u[j] must be true
        opt.add( If(b[i] == j, u[j], True) )

# Within‐bin & fit constraints
for i, (wi, hi) in enumerate(items):
    # item must lie within its bin bounds
    opt.add( x[i] >= 0 )
    opt.add( y[i] >= 0 )
    opt.add( x[i] + wi <= W )
    opt.add( y[i] + hi <= H )

# Non‐overlap: for each pair of items i<j, if they are in same bin then they must not overlap
for i in range(n):
    for j in range(i+1, n):
        wi, hi = items[i]
        wj, hj = items[j]
        # require: if b[i]==b[j] then ( item i is left or right or above or below j )
        no_overlap = Or(
            x[i] + wi <= x[j],
            x[j] + wj <= x[i],
            y[i] + hi <= y[j],
            y[j] + hj <= y[i]
        )
        opt.add( If(b[i] == b[j], no_overlap, True) )

# Link u[j] to whether any item uses bin j:
# (At least one item with b[i]==j) ⇒ u[j]
for j in range(m):
    # if u[j] is false, then no item i can have b[i]==j
    for i in range(n):
        opt.add( If(u[j] == False, b[i] != j, True) )

# Objective: minimize number of used bins
opt.minimize( sum( If(u[j], 1, 0) for j in range(m) ) )

# --- Solve and display ---
if opt.check() == None:
    print("Solver failed.")
else:
    model = opt.model()
    used_bins = [j for j in range(m) if model.evaluate(u[j])]
    print("Used bins:", used_bins)
    for j in used_bins:
        print(" Bin", j, "contains items:")
        for i in range(n):
            if model.evaluate(b[i]).as_long() == j:
                xi = model.evaluate(x[i]).as_long()
                yi = model.evaluate(y[i]).as_long()
                print(f"   Item {i} size={items[i]} at (x={xi}, y={yi})")
    print("Total bins used =", len(used_bins))