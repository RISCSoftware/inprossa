import ast
from Translator.Objects.Predicate import Predicate
from Translator.Objects.CodeBlock import CodeBlock
from Translator.Objects.MiniZincObject import MiniZincObject
from Translator.Objects.Constant import Constant


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
        self.objects = {}            # class_name -> MiniZincObject
        self.top_level_stmts = []
        # TODO think about how to handle maximising/minimising
        self.objective = None        # ('minimize', 'expr') or ('maximize', 'expr')

    def unroll_translation(self):
        """Returns the compiled MiniZinc code that corresponds to the given Python code."""
        self.parse()
        return self.compile()

    def parse(self):
        """
        Parse the input code collection functions as predicates
        and creating a list of top-level statements.
        """
        tree = ast.parse(self.code)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                mz_obj = MiniZincObject(node, predicates_registry=self.predicates)
                self.objects[mz_obj.name] = mz_obj
            elif isinstance(node, ast.FunctionDef):
                pred = Predicate(node, predicates=self.predicates)
                self.predicates[pred.name] = pred
            else:
                self.top_level_stmts.append(node)
        return self

    def compile(self):
        """Execute top-level block with access to registered predicates"""
        block = CodeBlock(predicates=self.predicates)
        block.run(self.top_level_stmts, loop_scope={})

        parts = []

        # 1) Predicate definitions
        for name in sorted(self.predicates.keys()):
            parts.append(self.predicates[name].emit_definition())

        # 2) Constants (symbols)
        parts += self.get_symbol_declarations(block)

        # 3) Arrays for versioned variables in top-level code
        parts += self.get_vars_declrs(block)

        # 4) Constraints from top-level code (incl. predicate calls as 'constraint f(...)')
        parts += self.get_constraints(block)

        # 5) Solve (default)
        if self.objective is None:
            parts.append("solve satisfy;")
        else:
            sense, expr = self.objective
            parts.append(f"solve {sense} {expr};")

        return "\n".join(parts)

    def get_symbol_declarations(self, block):
        """Declare constants as MiniZinc symbols (not evolving)."""
        decls = []
        for name, val in block.symbol_table.items():
            constant = Constant(name, val)
            decls.append(constant.to_minizinc())
        return decls
    
    def get_vars_declrs(self, block):
        """Get all variable declarations (evolving and non-evolving)."""
        return [declr.to_minizinc() for declr in block.all_variable_declarations.values()]

    def get_constraints(self, block):
        return [str(c) for c in block.constraints if c is not None]
    
    