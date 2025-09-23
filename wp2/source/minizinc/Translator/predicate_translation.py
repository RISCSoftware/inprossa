import ast
import textwrap


class Constraint:
    def __init__(self, expression="", conditions=[]):
        self.conditions = conditions
        self.expression = expression

    def __str__(self):
        if not self.conditions:
            return f"constraint {self.expression};"
        else:
            cond_str = " /\\ ".join(self.conditions)
            return f"constraint {cond_str} -> {self.expression};"


class MiniZincTranslator:
    def __init__(self, code):
        self.variable_index = {}
        self.constraints = []
        self.functions = {}
        self.code = textwrap.dedent(code)  # <-- Clean indentation here!

    def parse_code(self):
        tree = ast.parse(self.code)
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                func_name = stmt.name
                args = [arg.arg for arg in stmt.args.args]
                self.functions[func_name] = (args, stmt.body)

    def rewrite_expr(self, expr, var_mapping):
        if isinstance(expr, ast.BinOp):
            left = self.rewrite_expr(expr.left, var_mapping)
            right = self.rewrite_expr(expr.right, var_mapping)
            op = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "div",
                ast.Mod: "mod",
                ast.Pow: "^"
            }.get(type(expr.op), "?")
            return f"({left} {op} {right})"
        elif isinstance(expr, ast.Name):
            return var_mapping.get(expr.id, expr.id)
        elif isinstance(expr, ast.Constant):
            return str(expr.value)
        else:
            return ast.unparse(expr)

    def generate_predicates(self):
        predicates = []
        for name, (args, body) in self.functions.items():
            var_index = {}
            constraints = []
            input_decls = []
            var_decls = []

            for i, arg in enumerate(args, start=1):
                input_decls.append(f"int: input_{i}")
                var_index[arg] = 1
                var_decls.append(f"array[1..1] of var int: {arg}")
                constraints.append(f"{arg}[1] = input_{i}")

            for stmt in body:
                if isinstance(stmt, ast.Assign):
                    var = stmt.targets[0].id
                    rhs = self.rewrite_expr(stmt.value, {k: f"{k}[{v}]" for k, v in var_index.items()})

                    if var not in var_index:
                        var_index[var] = 1
                        var_decls.append(f"array[1..1] of var int: {var}")
                    else:
                        var_index[var] += 1
                        for i, decl in enumerate(var_decls):
                            if decl.endswith(f" {var}"):
                                var_decls[i] = f"array[1..{var_index[var]}] of var int: {var}"

                    constraints.append(f"{var}[{var_index[var]}] = {rhs}")

                elif isinstance(stmt, ast.Return):
                    returns = stmt.value.elts if isinstance(stmt.value, ast.Tuple) else [stmt.value]
                    for i, ret_expr in enumerate(returns, start=1):
                        ret_var = ret_expr.id
                        constraints.append(f"output_{i} = {ret_var}[{var_index[ret_var]}]")

            output_decls = [f"var int: output_{i}" for i in range(1, len(returns)+1)]
            header = f"predicate {name}({', '.join(input_decls + output_decls + var_decls)}) ="
            body_constraints = " /\\\n    ".join(f"constraint {c}" for c in constraints)
            predicates.append(f"{header}\n    (\n    {body_constraints}\n    );")

        return predicates

if __name__ == "__main__":
    code = """
    def f(a, b):
        c = a + b
        d = a * b
        c = c * d
        return c, d
    """
    translator = MiniZincTranslator(code)
    translator.parse_code()
    predicates = translator.generate_predicates()
    for pred in predicates:
        print(pred)
