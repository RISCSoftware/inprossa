from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator
from src.optdsl.solver.Minizinc_solver import MiniZincRunner


class DSLSolver:
    def __init__(self,
                 code: str,
                 solver_name="chuffed",
                 timelimit: float = 10):
        self.code = code
        self.solver_name = solver_name
        self.timelimit = timelimit

    def run(self):
        translator = MiniZincTranslator(self.code)
        model = translator.unroll_translation()

        runner = MiniZincRunner(
            solver_name=self.solver_name,
            timelimit=self.timelimit
            )
        result = runner.run(model)
        return result
    