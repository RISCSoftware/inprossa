import ast
from typing import Union
from Translator.Objects.DSTypes import DSList, compute_type


class Constant:
    def __init__(self,
                 name: str,
                 stmt_value: str = None,
                 type_: Union[int, float, bool, DSList] = "int",
                 code_block=None,
                 loop_scope=None):
        self.name = name
        self.type = type_
        self.loop_scope = {} if loop_scope is None else loop_scope

        if stmt_value is not None:
            try:
                # Substitute known constants before evaluation
                tree = self.substitute_constants(stmt_value, code_block.constant_table)

                # Try evaluating the AST directly (safe subset)
                evaluated = self.safe_eval(tree)

                # rewrite_expr if not purely evaluable
                if evaluated is None:
                    rewritten = code_block.rewrite_expr(tree, get_numeral=True, loop_scope=self.loop_scope)
                    evaluated = self.to_number(rewritten)

                self.value = evaluated
            except Exception as e:
                # fallback if not evaluable
                self.value = stmt_value
        else:
            self.value = stmt_value


    def to_minizinc(self) -> str:
        return f"{self.type.representation()}: {self.name} = {self.value}"

    def to_number(self, s):
        # Convert string to numeric if possible
        if isinstance(s, (int, float, list)):
            return s
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s


    def substitute_constants(self, tree, const_table):
        """Replace ast.Name nodes with ast.Constant if known."""
        class ConstSubstituter(ast.NodeTransformer):
            def __init__(self, table):
                self.table = table
            def visit_Name(self, node):
                if node.id in self.table:
                    val = self.table[node.id].value
                    # 🔹 Allow nested lists or numbers
                    return ast.copy_location(ast.Constant(value=val), node)
                return node
        return ConstSubstituter(const_table).visit(tree)


    def safe_eval(self, tree):
        """
        Try to evaluate simple numeric/list expressions safely after constant substitution.
        Only allows literals, lists, tuples, binops, and numeric constants.
        """
        allowed_nodes = (
            ast.Expression, ast.Constant, ast.List, ast.Tuple,
            ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
            ast.UnaryOp, ast.USub, ast.UAdd
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return None  # contains something too complex → skip evaluation

        try:
            return eval(compile(tree, filename="<ast>", mode="eval"))
        except Exception:
            return None
