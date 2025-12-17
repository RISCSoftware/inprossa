import subprocess

import re
import ast
from typing import Any, Dict
#from minizinc import Model, Solver, Instance
import threading
import pymzn
from pymzn import Status

from constants import DEBUG_MODE_ON

lock = threading.Lock()


def minizinc_item_to_dict(s: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    parts = [p.strip() for p in s.split(';') if p.strip()]
    for part in parts:
        if '=' not in part:
            continue
        key, val = part.split('=', 1)
        key = key.strip()
        val = val.strip()

        # Convert record syntax: (field: v, ...) → { "field": v, ...}
        py = val.replace('(', '{').replace(')', '}')
        py = re.sub(r'([A-Za-z_]\w*)\s*:', r'"\1":', py)

        # Convert MiniZinc boolean literals to Python booleans
        py = (re.compile(r'\b(true|false)\b', flags=re.IGNORECASE)
              .sub(lambda m: m.group(1).lower().capitalize(), py))

        try:
            parsed = ast.literal_eval(py)
        except Exception as e:
            raise ValueError(f"Cannot parse value for {key!r}.\nTransformed: {py!r}\nError: {e}")
        result[key] = parsed
    return result


class MiniZincSolver:
    def solve_with_command_line_minizinc(self, minizinc_code: str, is_terminal_node: bool = False):
        # write the MiniZinc model to temp.mzn
        with lock:
            with open("temp.mzn", "w", encoding="utf-8") as f:
                f.write(minizinc_code)

            # run minizinc on the file
            try:
                if is_terminal_node:
                    result = subprocess.Popen(
                        ["minizinc",
                                    "--solver", "gecode",
                                     "--statistics",
                                     "--output-mode", "item",
                                     "--time-limit", "300000",
                                     "temp.mzn"],
                        text=True,
                        stdout = subprocess.PIPE, stderr = subprocess.PIPE
                    )
                else:
                    result = subprocess.Popen(
                        ["minizinc",
                         "--solver", "gecode",
                         "--statistics",
                         "--output-mode", "item",
                         "--time-limit", "60000",
                         "temp.mzn"],
                        text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                try:
                    solver_output, errs = result.communicate(timeout=320)
                except subprocess.TimeoutExpired:
                    if DEBUG_MODE_ON: print("Minizinc failed the first time - lets try that again")
                    result.kill()  # or proc.terminate()
                    solver_output, errs = result.communicate()
                result.terminate()
                solver_output = solver_output
            except KeyboardInterrupt:
                print("Caught Ctrl-C! Probably MiniZinc died again ...")
                print(minizinc_code)
                return "Unknown", None

        print("Return code:", result.returncode)
        if solver_output:
            if "unknown" not in solver_output.lower() and "unsatisfiable" not in solver_output.lower():
                solve_time = None
                m = re.search(r"solveTime\s*=\s*([0-9]*\.?[0-9,e,-]+)", solver_output)
                if m:
                    solve_time = float(m.group(1))
                filtered_result = "\n".join(line for line in solver_output.splitlines() if ("%" not in line
                                                                                              and "---" not in line
                                                                                              and "===" not in line))
                parsed_solution = minizinc_item_to_dict(filtered_result)
                print("Solver Output:\n", parsed_solution)
                print("Solve time (sec):\n", solve_time)
                return parsed_solution, solve_time
            else:
                print("Output:\n", solver_output)
                return solver_output, None
        if errs:
            print("Errors:\\n", errs)
            return f"Error: {errs}", None
        return None, None

    '''
    def solve_with_python_minizinc(self, minizinc_code: str):
        # 1. Create a MiniZinc model
        model = Model()
        model.add_string(minizinc_code)

        # 2. Choose a solver
        gecode = Solver.lookup("gecode")

        # 3. Bind model to solver to create an instance
        inst = Instance(gecode, model)

        # 4. Solve
        try:
            result = inst.solve(time_limit=timedelta(milliseconds=60000), output_mode="item", output_objective=True)

            # 5. Inspect result
            solver_output = result.solution
            if solver_output:
                if "unknown" not in solver_output.lower() and "unsatisfiable" not in solver_output.lower():
                    solve_time = result.statistics["solve_time"]
                    filtered_result = "\n".join(line for line in solver_output.splitlines() if ("%" not in line
                                                                                                  and "---" not in line
                                                                                                  and "===" not in line))
                    parsed_solution = self.minizinc_item_to_dict(filtered_result)
                    print("Solver Output:\n", parsed_solution)
                    print("Solve time (sec):\n", solve_time)
                    return parsed_solution, solve_time
                else:
                    print("Output:\n", solver_output)
                    return solver_output, None
            else:
                return None, None
        except Exception as e:
            print(f"Solver failed: {e}")
            return None, None
    '''

    def solve_with_pymnz(self, minizinc_code: str):
        solns = pymzn.minizinc(minizinc_code, output_mode="item", timeout=60)
        if solns and solns.status != Status.ERROR:
            if solns.status != Status.UNKNOWN and solns.status != Status.UNSATISFIABLE:
                solve_time = None
                m = re.search(r"solveTime\s*=\s*([0-9]*\.?[0-9,e,-]+)", solns.log)
                if m:
                    solve_time = float(m.group(1))
                solver_output = minizinc_item_to_dict(solns[0])
                print("Solver Output:\n", solver_output)
                print("Solve time (sec):\n", solve_time)
                return solver_output, solve_time
            else:
                print("Output:\n", "unsatisfiable or unknown")
                return "unsatisfiable or unknown", None
        else:
            return "Semantic error", None
