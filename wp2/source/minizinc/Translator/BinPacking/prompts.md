Assume I have a python function that evaluates an assignment in discrete optimization. The function tells us whether 
- bool: any constraint was violated (or none)
- if no contstraint was violated, the objective

This function also gets all problem parameters from the instance.

Now I want to write a solver that only gets the above function and parameters.
Would I run into problems if I run tree based solvers?

---

How to make partial assignments possible here?
Should we check
- being valid (even for partial)
- being partial (even for invalid)
- the objective

in different functions? Do you agree with this split?

```python
BOX_CAPACITIES : DSList(4, DSInt()) = [5, 5, 5, 5]
ITEM_WEIGHTS : DSList(5, DSInt()) = [4, 2, 5, 3, 1]

NBOXES : int = 4
NITEMS : int = 5

assignments: DSList(NITEMS, DSInt(1, NBOXES))

def not_exceed(assignments: DSList(NITEMS, DSInt(1, NBOXES))):
    cap: DSList(NBOXES, DSInt(0, sum(ITEM_WEIGHTS)))
    for i in range(1, NBOXES + 1):
        cap[i] = 0
        for j in range(1, NITEMS + 1):
            if assignments[j] == i:
                cap[i] = cap[i] + ITEM_WEIGHTS[j]

        assert cap[i] <= BOX_CAPACITIES[i] # + slack
        if cap[i] > 0:
            objective = objective + 1

not_exceed(assignments)
```
