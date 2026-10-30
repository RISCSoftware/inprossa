from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator
from src.optdsl.solver.Minizinc_solver import MiniZincRunner


class DSLSolver:
    def __init__(self,
                 code: str,
                 solver_name="chuffed",
                 timelimit: float = 10,
                 dsl_index_base: int = 0,
                 minizinc_executable=None,
                 progress: bool = False,
                 progress_interval: float = 5.0):
        self.code = code
        self.solver_name = solver_name
        self.timelimit = timelimit
        if dsl_index_base not in (0, 1):
            raise ValueError("dsl_index_base must be 0 or 1")
        self.dsl_index_base = dsl_index_base
        self.minizinc_executable = minizinc_executable
        self.progress = progress
        self.progress_interval = progress_interval

    def translate(self):
        """Translate the DSL to MiniZinc text WITHOUT invoking a solver.

        Mirrors run(): builds the MiniZinc model from the DSL source and
        returns it as a string. Useful for inspecting/capturing the generated
        .mzn (e.g. run_minizinc.py --dump-mzn).
        """
        translator = MiniZincTranslator(self.code, dsl_index_base=self.dsl_index_base)
        return translator.unroll_translation()

    def run(self):
        translator = MiniZincTranslator(self.code, dsl_index_base=self.dsl_index_base)
        model = translator.unroll_translation()
        runner = MiniZincRunner(
            solver_name=self.solver_name,
            timelimit=self.timelimit,
            minizinc_executable=self.minizinc_executable,
            progress=self.progress,
            progress_interval=self.progress_interval,
            )
        result = runner.run(model)
        return result
    