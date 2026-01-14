import tempfile
import minizinc

class Timeout:
    def __init__(self, timelimit):
        self.timelimit = timelimit
    def total_seconds(self):
        return self.timelimit

class MiniZincRunner:
    def __init__(self, solver_name="gecode", timelimit: int = 10):
        self.solver = minizinc.Solver.lookup(solver_name)
        self.timelimit = timelimit

    def run(self, code_string: str, data: dict = None):
        """
        Run MiniZinc code from a string.
        Optionally pass a Python dict as data (converted to MiniZinc).
        Returns a MiniZinc result object.
        """
        # create a temporary .mzn file
        with tempfile.NamedTemporaryFile(suffix=".mzn", mode="w", delete=False) as tmp:
            tmp.write(code_string)
            tmp_path = tmp.name

        # create model
        model = minizinc.Model(tmp_path)

        # handle optional data
        if data:
            for k, v in data.items():
                model[k] = v

        # run
        instance = minizinc.Instance(self.solver, model)
        result = instance.solve(timeout=Timeout(self.timelimit))


        return result
