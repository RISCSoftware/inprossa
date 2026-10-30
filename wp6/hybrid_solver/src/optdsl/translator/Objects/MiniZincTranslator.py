import ast
from typing import Any

from src.optdsl.translator.Objects.Predicate import Predicate
from src.optdsl.translator.Objects.CodeBlock import CodeBlock
from src.optdsl.translator.Objects.DSTypes import DSBool, DSFloat, DSInt, DSList, DSType


class MiniZincTranslator:
    """
    Top-level orchestrator:
      - Parses Python code into AST
      - Registers function definitions as Predicates
      - Sends top-level executable statements to a CodeBlock
      - Assembles final MiniZinc text (predicate defs, symbols, arrays, scalars, constraints, solve)
    """
    def __init__(self, code, dsl_index_base: int = 0):
        self.code = code
        if dsl_index_base not in (0, 1):
            raise ValueError("dsl_index_base must be 0 or 1")
        self.dsl_index_base = dsl_index_base
        self.constants = dict()          # name -> Constant
        self.types = dict()              # name -> DS... type
        self.predicates = dict()         # name -> Predicate
        self.records = dict()            # class_name -> MiniZincRecord
        self.top_level_stmts = []
        # TODO think about how to handle maximising/minimising
        self.objective = None        # ('minimize', 'expr') or ('maximize', 'expr')
        self.warm_start_spec: dict[str, Any] | None = None

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
            # 0) Collect Global Constants
            # if is an annassignment and lhs is uppercase
            # For now the constant should be defined in annassignment
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id.isupper():
                const_name = node.target.id
                 # Evaluate type
                code_block = CodeBlock(
                    constant_table=self.constants,
                    predicates=self.predicates,
                    types=self.types,
                    dsl_index_base=self.dsl_index_base,
                )
                code_block.run([node], loop_scope={})
                self.constants[const_name] = code_block.constant_table[const_name]

            # 1) type definitions -> MiniZinc type definitions
            if (isinstance(node, ast.Assign) and
                isinstance(node.value, ast.Call) and  # right-hand side is a call
                isinstance(node.value.func, ast.Name) and
                node.value.func.id.startswith("DS") and
                len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name)):

                type_name = node.targets[0].id
                mz_type = DSType(
                    node.value,
                    type_name,
                    known_types=self.types,  # type: ignore[arg-type]
                    constant_table=self.constants,
                ).return_type()
                self.types[type_name] = mz_type

            # 2) function definitions -> Predicates
            elif isinstance(node, ast.FunctionDef):
                if self._is_warm_start_function(node):
                    self.warm_start_spec = self._parse_warm_start_function(node)
                    continue

                # to ast visualisation
                pred = Predicate(node,
                                 predicates=self.predicates,
                                 constant_table=self.constants,
                                 types=self.types,
                                 dsl_index_base=self.dsl_index_base)
                self.predicates[pred.name] = pred
            
            # 3) Set objective (minimize/maximize) 
            elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Name) and
                (node.value.func.id == "minimize" or
                 node.value.func.id == "maximize")):
                self.objective = (node.value.func.id, ast.unparse(node.value.args[0]))
            else:
                self.top_level_stmts.append(node)
        return self

    def compile(self):
        """Execute top-level block with access to registered predicates"""
        block = CodeBlock(
            constant_table=self.constants,
            predicates=self.predicates,
            types=self.types,
            dsl_index_base=self.dsl_index_base)
        block.run(self.top_level_stmts, loop_scope={})

        parts = []

        # 0) Type definitions
        for name, _type in self.types.items():
            parts.append(_type.emit_definition())

        # 1) Predicate definitions
        for name in sorted(self.predicates.keys()):
            parts.append(self.predicates[name].emit_definition())

        # 2) Constants (symbols)
        parts += self.get_symbol_declarations(block)

        # 3) Arrays for versioned variables in top-level code
        parts += self.get_vars_declrs(block)

        # 3.5) Optional warm start declarations from DSL metadata
        parts += self.get_warm_start_declarations(block)

        # 4) Constraints from top-level code (incl. predicate calls as 'constraint f(...)')
        parts += self.get_constraints(block)

        # 4.5) Optional objective bounds from warm start metadata
        parts += self.get_warm_start_objective_bounds(block)

        # 5) Solve (default)
        parts.append(self.get_objective(block))
        return ";\n".join(parts)
    
    # TODO these three methods could be moved to CodeBlock?

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

    def get_warm_start_declarations(self, block):
        if self.warm_start_spec is None:
            return []

        hint_assignments = self.warm_start_spec.get("hints", {})
        if not isinstance(hint_assignments, dict):
            raise ValueError("warm_start hints must be a dictionary")

        declarations: list[str] = []
        for variable_name, hint_value in hint_assignments.items():
            if variable_name not in block.variable_table:
                continue
            var_obj = block.variable_table[variable_name]
            hint_decl = self._build_hint_declaration(var_obj, hint_value)
            if hint_decl is not None:
                declarations.append(hint_decl)
        return declarations

    def get_warm_start_objective_bounds(self, block):
        if self.warm_start_spec is None or self.objective is None:
            return []

        objective_variable_name = self.objective[1]
        if objective_variable_name not in block.variable_table:
            return []

        objective_var = block.variable_table[objective_variable_name]
        objective_expr = objective_var.versioned_name()

        bounds: list[str] = []
        lower_bound = self.warm_start_spec.get("lower_bound")
        upper_bound = self.warm_start_spec.get("upper_bound")
        if lower_bound is not None:
            bounds.append(f"constraint {objective_expr} >= {self._mzn_literal(lower_bound)}")
        if upper_bound is not None:
            bounds.append(f"constraint {objective_expr} <= {self._mzn_literal(upper_bound)}")
        return bounds
    
    def get_objective(self, block):
        solve_annotations = self._get_warm_start_solve_annotations(block)
        if solve_annotations:
            solve_prefix = "solve\n  :: " + "\n  :: ".join(solve_annotations) + "\n  "
        else:
            solve_prefix = "solve "

        # Look for 'objective' variable in block
        if self.objective is not None:
            obj_type, obj_expr = self.objective
            obj_var = block.variable_table[obj_expr]
            obj_var_ver_name = obj_var.versioned_name()
            return f"{solve_prefix}{obj_type} {obj_var_ver_name};"
        return f"{solve_prefix}satisfy;"

    def _is_warm_start_function(self, node: ast.FunctionDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "warm_start":
                return True
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "warm_start":
                return True
        return False

    def _parse_warm_start_function(self, node: ast.FunctionDef) -> dict[str, Any]:
        decorator = None
        for candidate in node.decorator_list:
            if isinstance(candidate, ast.Name) and candidate.id == "warm_start":
                decorator = candidate
                break
            if isinstance(candidate, ast.Call) and isinstance(candidate.func, ast.Name) and candidate.func.id == "warm_start":
                decorator = candidate
                break

        if decorator is None:
            raise ValueError("Missing warm_start decorator")

        lower_bound = None
        upper_bound = None
        if isinstance(decorator, ast.Call):
            for kw in decorator.keywords:
                if kw.arg in ("lower_bound", "lb"):
                    lower_bound = ast.literal_eval(kw.value)
                elif kw.arg in ("upper_bound", "ub"):
                    upper_bound = ast.literal_eval(kw.value)
                elif kw.arg == "bounds":
                    bounds = ast.literal_eval(kw.value)
                    if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
                        lower_bound, upper_bound = bounds

        return_stmt = None
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                return_stmt = stmt
                break

        if return_stmt is None:
            raise ValueError("@warm_start function must return a dictionary of hints")

        if return_stmt.value is None:
            raise ValueError("@warm_start function must return a dictionary")

        hints = ast.literal_eval(return_stmt.value)
        if not isinstance(hints, dict):
            raise ValueError("@warm_start return value must be a dictionary")

        return {
            "hints": hints,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }

    def _mzn_literal(self, value: Any) -> str:
        if value is None:
            return "<>"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(self._mzn_literal(v) for v in value) + "]"
        if isinstance(value, tuple):
            return "[" + ", ".join(self._mzn_literal(v) for v in value) + "]"
        raise ValueError(f"Unsupported warm_start literal value: {value!r}")

    def _hint_type(self, type_obj) -> str | None:
        if isinstance(type_obj, DSInt):
            return "opt int"
        if isinstance(type_obj, DSFloat):
            return "opt float"
        if isinstance(type_obj, DSBool):
            return "opt bool"
        if isinstance(type_obj, DSList):
            elem_hint_type = self._hint_type(type_obj.elem_type)
            if elem_hint_type is None:
                return None
            return f"array[1..{type_obj.length}] of {elem_hint_type}"
        return None

    def _build_hint_declaration(self, var_obj, hint_value: Any) -> str | None:
        hint_type = self._hint_type(var_obj.type)
        if hint_type is None:
            return None
        return f"{hint_type}: {var_obj.name}_hint = {self._mzn_literal(hint_value)}"

    def _warm_start_target_expr(self, var_obj) -> tuple[str, bool]:
        target_expr = var_obj.versioned_name()
        is_scalar = not isinstance(var_obj.type, DSList)
        return target_expr, is_scalar

    def _get_warm_start_solve_annotations(self, block) -> list[str]:
        if self.warm_start_spec is None:
            return []
        hints = self.warm_start_spec.get("hints", {})
        if not isinstance(hints, dict):
            return []

        annotations: list[str] = []
        for variable_name in hints.keys():
            if variable_name not in block.variable_table:
                continue
            var_obj = block.variable_table[variable_name]
            target_expr, is_scalar = self._warm_start_target_expr(var_obj)
            hint_name = f"{var_obj.name}_hint"
            if is_scalar:
                annotations.append(f"warm_start([{target_expr}], [{hint_name}])")
            else:
                annotations.append(f"warm_start({target_expr}, {hint_name})")
        return annotations

