import tempfile
import minizinc

class MiniZincRunner:
    def __init__(self, solver_name="gecode"):
        self.solver = minizinc.Solver.lookup(solver_name)

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
        result = instance.solve()

        return result
