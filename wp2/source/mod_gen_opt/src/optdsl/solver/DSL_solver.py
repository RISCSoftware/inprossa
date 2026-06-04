from src.optdsl.translator.Objects.MiniZincTranslator import MiniZincTranslator
from src.optdsl.solver.Minizinc_solver import MiniZincRunner


class DSLSolver:
    def __init__(self,
                 code: str,
                 solver_name="chuffed",
                 timelimit: float = 10,
                 dsl_index_base: int = 0):
        self.code = code
        self.solver_name = solver_name
        self.timelimit = timelimit
        if dsl_index_base not in (0, 1):
            raise ValueError("dsl_index_base must be 0 or 1")
        self.dsl_index_base = dsl_index_base

    def run(self):
        translator = MiniZincTranslator(self.code, dsl_index_base=self.dsl_index_base)
        model = translator.unroll_translation()
        runner = MiniZincRunner(
            solver_name=self.solver_name,
            timelimit=self.timelimit
            )
        result = runner.run(model)
        return result
    