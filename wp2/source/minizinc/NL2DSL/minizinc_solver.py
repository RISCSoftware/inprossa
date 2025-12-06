import json
import subprocess

import re
import ast
from datetime import timedelta
from typing import Any, Dict
from minizinc import Model, Solver, Instance


class MiniZincSolver():
    def solve_with_command_line_minizinc(self, minizinc_code: str):
        # write the MiniZinc model to temp.mzn
        with open("temp.mzn", "w", encoding="utf-8") as f:
            f.write(minizinc_code)

        # run minizinc on the file
        result = subprocess.run(
            ["minizinc",
                        "--solver", "gecode",
                         "--no-intermediate",
                         "--output-time",
                         "--output-objective",
                         "--statistics",
                         "--output-mode", "item",
                         "--time-limit", "60000",
                         "temp.mzn"],
            capture_output=True,
            text=True
        )
        #solver_output, err = result.communicate()
        #result.terminate()
        solver_output = result.stdout

        print("Return code:", result.returncode)
        if solver_output:
            if "unknown" not in solver_output.lower() and "unsatisfiable" not in solver_output.lower():
                filtered_result = ""
                solve_time = None
                m = re.search(r"solveTime\s*=\s*([0-9]*\.?[0-9,e,-]+)", solver_output)
                if m:
                    solve_time = float(m.group(1))
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
        if result.stderr:
            print("Errors:\\n", result.stderr)
        return None, None


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


    # def solve_with_pymnz(self, minizinc_code: str):
    '''
    def solve_with_pymnz(self, minizinc_code: str):
        solns = pymzn.minizinc(minizinc_code, output_mode="item")
        parsed = self.minizinc_item_to_dict(solns[0])
        parsed_solution = json.dumps(parsed, indent=4)
        print(parsed_solution)
    '''


    def minizinc_item_to_dict(self, s: str) -> Dict[str, Any]:
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
