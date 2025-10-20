import ast
from Translator.Objects.Predicate import Predicate
from Translator.Objects.CodeBlock import CodeBlock
from Translator.Objects.MiniZincObject import MiniZincObject
from Translator.Objects.Constant import Constant
from Translator.Objects.DSTypes import DSRecord, DSType


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
        self.constants = dict()          # name -> Constant
        self.types = dict()              # name -> DS... type
        self.predicates = dict()         # name -> Predicate
        self.records = dict()            # class_name -> MiniZincRecord
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
        # for node in tree.body:
        #     print(ast.dump(node, indent=4))
        for node in tree.body:
            # 0) Constants
            # if is an annassignment and lhs is uppercase
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id.isupper():
                const_name = node.target.id
                 # Evaluate type
                code_block = CodeBlock(constant_table=self.constants, predicates=self.predicates, types=self.types)
                code_block.run([node], loop_scope={})
                self.constants[const_name] = code_block.constant_table[const_name]
            # For now the constant should be defined in annassignment
            # # if is an assignment and lhs is uppercase
            # elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id.isupper():
            #     const_name = node.targets[0].id
            #     # Evaluate type
            #     self.constants[const_name].add_value(ast.unparse(node.value))

            # 1) type definitions -> MiniZinc type definitions
            if (isinstance(node, ast.Assign) and
                isinstance(node.value, ast.Call) and  # right-hand side is a call
                isinstance(node.value.func, ast.Name) and
                node.value.func.id.startswith("DS")):
                        type_name = node.targets[0].id
                        mz_type = DSType(node.value, type_name).return_type()
                        self.types[type_name] = mz_type

            # 2) class definitions -> MiniZincObject
            elif isinstance(node, ast.ClassDef):
                mz_obj = MiniZincObject(node, predicates_registry=self.predicates)
                self.objects[mz_obj.name] = mz_obj
            # 3) function definitions -> Predicates
            elif isinstance(node, ast.FunctionDef):
                print("CTABLE BEFORE PREDICATE", self.constants)
                pred = Predicate(node,
                                 predicates=self.predicates,
                                 constant_table=self.constants)
                self.predicates[pred.name] = pred
            else:
                self.top_level_stmts.append(node)
        return self

    def compile(self):
        """Execute top-level block with access to registered predicates"""
        block = CodeBlock(
            constant_table=self.constants,
            predicates=self.predicates,
            types=self.types)
        block.run(self.top_level_stmts, loop_scope={})

        parts = []

        # 0) Type definitions
        for name, _type in self.types.items():
            if isinstance(_type, DSRecord):
                parts.append(_type.emit_definition(self.types.keys()))
            else:
                parts.append(_type.emit_definition())

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
        return ";\n".join(parts)

    def get_symbol_declarations(self, block):
        """Declare constants as MiniZinc symbols (not evolving)."""
        decls = []
        for constant in block.constant_table.values():
            decls.append(constant.to_minizinc())
        return decls

    def get_vars_declrs(self, block):
        """Get all variable declarations (evolving and non-evolving)."""
        return [declr.to_minizinc() for declr in block.variable_table.values()]

    def get_constraints(self, block):
        return [str(c) for c in block.constraints if c is not None]
