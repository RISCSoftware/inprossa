import sys
print("DEBUG sys.executable =", sys.executable)
print("DEBUG sys.path[0:3] =", sys.path[:3])

import minizinc

solver_dict = minizinc.default_driver.available_solvers(refresh=True)

# solver_dict maps tags -> list[Solver]
for tag, solvers in solver_dict.items():
    for s in solvers:
        print(f"tag={tag:6s}  name={s.name:12s}  id={s.id}  tags={s.tags}")
