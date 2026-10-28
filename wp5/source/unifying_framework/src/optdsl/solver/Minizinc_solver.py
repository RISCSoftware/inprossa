import asyncio
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
import minizinc


class MiniZincRunner:
    def __init__(self, solver_name="cp-sat", timelimit: float = 100, minizinc_executable=None,
                 progress: bool = False, progress_interval: float = 5.0):
        self.solver_name = solver_name
        self.solver = minizinc.Solver.lookup(solver_name)
        self.timelimit = timelimit
        # Optional path to a custom MiniZinc executable / its bin dir.
        # Defaults to whatever `minizinc` resolves to on PATH.
        self.minizinc_executable = minizinc_executable
        self.progress = progress
        self.progress_interval = progress_interval

    def _log(self, msg: str) -> None:
        # Guard so a broken stdout does not kill the solve.
        try:
            print(msg, flush=True, file=sys.stderr)
        except Exception:
            pass

    async def _collect_history_async(self, instance: minizinc.Instance, time_limit: timedelta, intermediate_solutions: bool):
        history = {"times": [], "objectives": []}
        final_result = None
        best_solution = None
        best_statistics = {}
        objective_bound = None
        n_solutions = 0
        start_wall = time.time()
        last_progress = 0.0
        last_heartbeat = 0.0

        # CP-SAT (OR-Tools) does not support the standard `--time-limit` flag
        # (it is absent from the solver's stdFlags).  Passing time_limit here
        # would append `--time-limit` which CP-SAT mis-handles (it even
        # overrides `--params` when both are present), so the solve could
        # outrun the budget by minutes.  Enforce the budget solely via
        # CP-SAT's own parameter and omit the library time_limit.
        if self.solver_name == "cp-sat":
            solutions_kwargs: dict = {
                "params": f"max_time_in_seconds: {int(time_limit.total_seconds())}"
            }
        else:
            solutions_kwargs = {
                "time_limit": time_limit,
            }
        solutions_kwargs["intermediate_solutions"] = intermediate_solutions

        async for res in instance.solutions(**solutions_kwargs):
            final_result = res
            # Merge statistics — later results may add more keys
            if res.statistics:
                best_statistics.update(res.statistics)
                bound = res.statistics.get("objectiveBound")
                if bound is not None:
                    objective_bound = bound
            if res.solution is not None:
                n_solutions += 1
                time_so_far = best_statistics.get("time")
                seconds = time_so_far.total_seconds() if hasattr(time_so_far, "total_seconds") else float(time_so_far or 0)
                history["times"].append(seconds)
                history["objectives"].append(res.objective)
                # Keep only data fields from the generated MiniZinc solution object.
                if hasattr(res.solution, "__dict__"):
                    best_solution = dict(vars(res.solution))
                else:
                    best_solution = {
                        name: value
                        for name in dir(res.solution)
                        if not name.startswith("__")
                        for value in [getattr(res.solution, name)]
                        if not callable(value)
                    }
                if self.progress:
                    now = time.time()
                    # Throttle: print the newest incumbent at most every
                    # progress_interval seconds (plus always the first one).
                    if n_solutions == 1 or (now - last_progress) >= self.progress_interval:
                        last_progress = now
                        self._log(
                            f"[minizinc] solution {n_solutions}: objective={res.objective} "
                            f"time={seconds:.2f}s elapsed_wall={now - start_wall:.2f}s"
                        )
            elif self.progress:
                # Intermediate status event without a full solution — log the
                # status so the user sees the solver is alive.
                now = time.time()
                if (now - last_heartbeat) >= self.progress_interval:
                    last_heartbeat = now
                    seconds = (time.time() - start_wall)
                    self._log(f"[minizinc] status={res.status} elapsed={seconds:.2f}s (no new solution yet)")

        if self.progress:
            self._log(
                f"[minizinc] done: {n_solutions} solution(s) in {time.time() - start_wall:.2f}s wall "
                f"(status={final_result.status if final_result is not None else None})"
            )

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

    def _minizinc_cli(self):
        if self.minizinc_executable:
            executable = str(self.minizinc_executable)
            if os.path.isdir(executable):
                return os.path.join(executable, "minizinc.exe")
            return executable
        driver = getattr(minizinc, "default_driver", None)
        executable = getattr(driver, "_executable", None) or getattr(driver, "executable", None)
        return str(executable) if executable else "minizinc"

    def _run_text_fallback(self, tmp_path: str, cause: Exception):
        """Fallback for MiniZinc JSON-stream bugs in minizinc-python/MiniZinc.

        MiniZinc 2.10.1 can solve some generated models in normal text mode but
        fails when minizinc-python forces `--output-mode json` (notably with
        chuffed and small woodcutting models). Return a minimal, structured
        result instead of crashing.
        """
        cmd = [self._minizinc_cli(), "--solver", self.solver_name, "--statistics"]
        if self.timelimit is not None:
            cmd.extend(["--time-limit", str(int(float(self.timelimit) * 1000))])
        cmd.append(tmp_path)
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = (completed.stdout or "") + (completed.stderr or "")

        if "UNSATISFIABLE" in output:
            status = "UNSATISFIABLE"
        elif "UNKNOWN" in output and "----------" not in output:
            status = "UNKNOWN"
        elif "==========" in output:
            status = "OPTIMAL_SOLUTION"
        elif "----------" in output:
            status = "SATISFIED"
        else:
            raise cause

        statistics = {}
        for key, value in re.findall(r"%%%mzn-stat: ([A-Za-z0-9_]+)=([^\r\n]+)", output):
            value = value.strip().strip('"')
            try:
                statistics[key] = float(value) if "." in value else int(value)
            except ValueError:
                statistics[key] = value
        objective = statistics.get("objective")
        n_solutions = int(statistics.get("nSolutions", 1 if "----------" in output else 0))
        statistics["nSolutions"] = n_solutions
        return {
            "best_solution": None,
            "statistics": statistics,
            "times": [],
            "objectives": [] if objective is None else [objective],
            "status": status,
            "total_time": total_time(statistics).total_seconds(),
            "objective_bound": None,
            "fallback": "minizinc-text",
            "fallback_reason": str(cause),
        }

    def run(self, code_string: str, data: dict = None):
        with tempfile.NamedTemporaryFile(suffix=".mzn", mode="w", delete=False) as tmp:
            tmp.write(code_string)
            tmp_path = tmp.name

        model = minizinc.Model(tmp_path)

        # Pass a custom MiniZinc executable only if the installed minizinc
        # library supports it (minizinc 0.10's Instance takes no executable
        # keyword; newer versions do). Fall back to the default `minizinc`.
        if self.minizinc_executable:
            try:
                instance = minizinc.Instance(self.solver, model, executable=self.minizinc_executable)
            except TypeError:
                instance = minizinc.Instance(self.solver, model)
        else:
            instance = minizinc.Instance(self.solver, model)

        time_limit = timedelta(seconds=float(self.timelimit))
        try:
            result = asyncio.run(self._collect_history_async(instance, time_limit, self.progress))
        except minizinc.MiniZincError as exc:
            message = str(exc)
            if "not an array expression" in message or "unexpected TEST" in message:
                result = self._run_text_fallback(tmp_path, exc)
            else:
                raise
        return result

    
def total_time(statistics):
    init = statistics.get("initTime", timedelta(0))
    solve = statistics.get("solveTime", timedelta(0))
    opt = statistics.get("optTime", timedelta(0))
    def as_timedelta(value):
        return value if hasattr(value, "total_seconds") else timedelta(seconds=float(value or 0))
    return as_timedelta(init) + as_timedelta(solve) + as_timedelta(opt)
