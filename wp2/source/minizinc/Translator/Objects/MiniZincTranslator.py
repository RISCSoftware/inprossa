import ast
from Translator.Objects.Predicate import Predicate
from Translator.Objects.CodeBlock import CodeBlock


class MiniZincTranslator:
    """
    Top-level orchestrator:
      - Parses Python code into AST
      - Registers function definitions as Predicates
      - Sends top-level executable statements to a CodeBlock
      - Assembles final MiniZinc text (predicate defs, symbols, arrays, scalars, constraints, solve)
    """
    def __init__(self, code):
        self.code = code
        self.predicates = {}         # name -> Predicate
        self.top_level_stmts = []
        self.objective = None        # ('minimize', 'expr') or ('maximize', 'expr')

    def parse(self):
        tree = ast.parse(self.code)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                pred = Predicate(node)
                self.predicates[pred.name] = pred
            else:
                self.top_level_stmts.append(node)
        return self

    def compile(self):
        # Execute top-level block with access to registered predicates
        block = CodeBlock(predicates=self.predicates)
        block.run(self.top_level_stmts, loop_scope={})

        parts = []

        # 1) Predicate definitions
        for name in sorted(self.predicates.keys()):
            parts.append(self.predicates[name].emit_definition())

        # 2) Constants (symbols)
        parts += block.get_symbol_declarations()

        # 3) Scalars (from predicate outputs)
        parts += block.get_scalar_decls()

        # 4) Arrays needed for predicate calls
        parts += block.get_extra_array_decls()

        # 5) Arrays for versioned variables in top-level code
        parts += block.get_var_array_decls()

        # 6) Constraints from top-level code (incl. predicate calls as 'constraint f(...)')
        parts += block.get_constraints()

        # 7) Solve (default)
        if self.objective is None:
            parts.append("solve satisfy;")
        else:
            sense, expr = self.objective
            parts.append(f"solve {sense} {expr};")

        return "\n".join(parts)

    def unroll_translation(self):
        self.parse()
        return self.compile()