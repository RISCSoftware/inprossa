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
import minizinc


class MiniZincRunner:
    def __init__(self, solver_name="or-tools", timelimit: float = 100):
        self.solver = minizinc.Solver.lookup(solver_name)
        self.timelimit = timelimit

    async def _collect_history_async(self, instance: minizinc.Instance, time_limit: timedelta):
        history = {"times": [], "objectives": []}
        final_result = None
        best_solution = None
        best_statistics = {}
        objective_bound = None
        async for res in instance.solutions(
            time_limit=time_limit,
            intermediate_solutions=True,
        ):
            final_result = res
            # Merge statistics — later results may add more keys
            if res.statistics:
                best_statistics.update(res.statistics)
                bound = res.statistics.get("objectiveBound")
                if bound is not None:
                    objective_bound = bound
            if res.solution is not None:
                time_so_far = best_statistics.get("time")
                history["times"].append(time_so_far.total_seconds() if hasattr(time_so_far, "total_seconds") else float(time_so_far or 0))
                history["objectives"].append(res.objective)
                best_solution = {name: getattr(res.solution, name) for name in dir(res.solution) if not name.startswith("__")}

        if final_result is None:
            return {
                "best_solution": None,
                "statistics": {},
                "times": history["times"],
                "objectives": history["objectives"],
                "status": None,
                "total_time": 0.0,
            }

        result = {
            "best_solution": best_solution,
            "statistics": best_statistics,
            "times": history["times"],
            "objectives": history["objectives"],
            "status": final_result.status,
            "total_time": total_time(best_statistics).total_seconds(),
            "objective_bound": objective_bound,
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
    from datetime import timedelta
    init = statistics.get("initTime", timedelta(0))
    solve = statistics.get("solveTime", timedelta(0))
    opt = statistics.get("optTime", timedelta(0))
    return init + solve + opt
