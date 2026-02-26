import tempfile
import minizinc

class Timeout:
    def __init__(self, timelimit):
        self.timelimit = timelimit
    def total_seconds(self):
        return self.timelimit

import asyncio
import tempfile
from datetime import timedelta
import time
import minizinc


class MiniZincRunner:
    def __init__(self, solver_name="gecode", timelimit: float = 100):
        self.solver = minizinc.Solver.lookup(solver_name)
        self.timelimit = timelimit

    async def _collect_history_async(self, instance: minizinc.Instance, time_limit: timedelta):
        history = {"times": [], "objectives": []}
        final_result = None
        initial_time = time.time()
        async for res in instance.solutions(
            time_limit=time_limit,
            intermediate_solutions=True,
        ):
            final_result = res
            if res.solution is not None:
                time_so_far = res.statistics.get("time").total_seconds()  # timedelta
                history["times"].append(time_so_far)
                history["objectives"].append(res.objective)
                best_solution = {name: getattr(res.solution, name) for name in dir(res.solution) if not name.startswith("__")}
        print("Final result:", final_result)
        result = {
            "best_solution": best_solution,
            "statistics": final_result.statistics,
            "times": history["times"],
            "objectives": history["objectives"],
            "status": final_result.status,
            "total_time": total_time(final_result.statistics).total_seconds()
        }
        return result

    def run(self, code_string: str, data: dict = None):
        with tempfile.NamedTemporaryFile(suffix=".mzn", mode="w", delete=False) as tmp:
            tmp.write(code_string)
            tmp_path = tmp.name

        model = minizinc.Model(tmp_path)

        instance = minizinc.Instance(self.solver, model)

        time_limit = timedelta(seconds=float(self.timelimit))
        result = asyncio.run(self._collect_history_async(instance, time_limit))
        return result

    
def total_time(statistics):
    if "optTime" in statistics:
        # it is an optimisation problem
        return statistics["initTime"] + statistics["solveTime"] + statistics["optTime"]
    else:
        return statistics["initTime"] + statistics["solveTime"]
