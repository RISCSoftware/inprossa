import ast
from typing import Optional


minizinc_original_types = {
    "int",
    "float",
    "string",
    "bool",
}


class ExpressionRewriter:
    def __init__(self, loop_scope = dict(), variable_table=dict(), constant_table=dict(), types=dict(), code_block=None):
        self.loop_scope = loop_scope
        if code_block is not None:
            self.variable_table = code_block.variable_table
            self.constant_table = code_block.constant_table
            self.types = code_block.types
        else:
            self.variable_table = variable_table
            self.constant_table = constant_table
            self.types = types
        self.code_block = code_block

    def get_expr_value(self, expr):
        """
        Converts a Python expression AST into a numerical value
        """
        string_expr = self.rewrite_expr(expr)
        ast_string_expr = ast.parse(string_expr).body[0]
        if isinstance(ast_string_expr, ast.Expr):
            ast_string_expr = ast_string_expr.value
        expr_value = ast_to_evaluation_constants(ast_string_expr, self.constant_table)
    
        return expr_value

    def rewrite_expr(self, expr):
        """
        Converts a Python expression AST into a MiniZinc-compatible string
        """

        if isinstance(expr, ast.BinOp):
            # Handle binary operations like x + y
            left = self.rewrite_expr(expr.left)
            right = self.rewrite_expr(expr.right)
            op = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "div",
                ast.Mod: "mod",
                ast.Pow: "^"
            }.get(type(expr.op), "?")
            return f"({left} {op} {right})"

        elif isinstance(expr, ast.Compare):
            # Handle comparisons like x < y or x == y
            left = self.rewrite_expr(expr.left)
            right = self.rewrite_expr(expr.comparators[0])
            op = {
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.Gt: ">",
                ast.GtE: ">=",
                ast.Eq: "=",
                ast.NotEq: "!="
            }.get(type(expr.ops[0]), "?")
            return f"({left} {op} {right})"

        elif isinstance(expr, ast.BoolOp):
            # Handle logical operations: and / or
            op = {
                # "and": "/\\",
                ast.And: "/\\",
                ast.Or: "\\/"
            }.get(type(expr.op), "?")
            values = [self.rewrite_expr(v) for v in expr.values]
            return f"({' {} '.format(op).join(values)})"
        
        elif isinstance(expr, ast.UnaryOp):
            # Handle unary operations: not / -
            if isinstance(expr.op, ast.Not):
                operand = self.rewrite_expr(expr.operand)
                return f"(not {operand})"
            elif isinstance(expr.op, ast.UAdd):
                operand = self.rewrite_expr(expr.operand)
                return f"(+{operand})"
            elif isinstance(expr.op, ast.USub):
                operand = self.rewrite_expr(expr.operand)
                return f"(-{operand})"

        elif isinstance(expr, ast.Name):
            name = expr.id

            # Loop variable
            if name in self.loop_scope:
                # Substituting loop var: name -> loop_scope[name]
                return str(self.loop_scope[name])

            # Constant (e.g., MAX_LENGTH)
            if name.isupper():
                return name

            # Now all variables must exist already
            # # Not constant, not loop var — must be a normal variable
            # if name not in self.variable_table:
            #     # First-time reference (e.g., used in an expression before assignment)
            #     self.new_evolving_variable(name)

            return self.variable_table[name].versioned_name()

        elif isinstance(expr, ast.Constant):
            # Handle literals: numbers, booleans
            return str(expr.value)

        elif isinstance(expr, ast.Subscript):
            # Handle array access like VALUES[i]
            base = self.rewrite_expr(expr.value)

            # Get the index expression, which can be a Name, Constant, or BinOp
            index = expr.slice

            index_str = self.rewrite_expr(index)
            # print the whole tree under expr
            return f"{base}[{index_str}]"
        
        elif isinstance(expr, ast.Attribute):
            # Handle attribute access like record.field
            value_str = self.rewrite_expr(expr.value)
            attr_str = expr.attr
            return f"{value_str}.{attr_str}"

        elif isinstance(expr, ast.Call):
            func_name = expr.func.id if isinstance(expr.func, ast.Name) else ast.unparse(expr.func)

            # --- Step 1: classify function ---
            quantifiers = {"exists", "forall", "any", "all"}
            aggregators = {"sum", "max", "min"}
            builtin_funcs = {"abs", "len"}

            # --- Step 2: handle built-ins early ---
            if func_name == "range":
                # MiniZinc uses '..' instead of range()
                args = [self.rewrite_expr(a) for a in expr.args]
                if len(args) == 1:
                    second = self.get_expr_value(expr.args[0]) - 1
                    print("SEcond:", second)
                    return f"1..{second}"
                elif len(args) == 2:
                    second = self.get_expr_value(expr.args[1]) - 1
                    print("SEcond:", second)
                    return f"{args[0]}..{second}"
                else:
                    raise ValueError("range() with step not supported in MiniZinc translation")
            if func_name == "abs":
                args = [self.rewrite_expr(a) for a in expr.args]
                return f"{func_name}({', '.join(args)})"
            
            if func_name == "len":
                arg_name = expr.args[0].id
                if arg_name in self.variable_table:
                    length = self.variable_table[arg_name].type.length
                elif arg_name in self.constant_table:
                    length = self.constant_table[arg_name].type.length
                return f"{length}"

            # --- Detect existing object of type record constructor call ---
            if func_name in self.types and hasattr(self.types[func_name], 'types_dict'):
                record_type = self.types[func_name]
                fields = list(record_type.types_dict.keys())

                field_value_pairs = []

                # --- 1. Positional arguments ---
                if expr.args:
                    for field_name, val_node in zip(fields, expr.args):
                        val_str = self.rewrite_expr(val_node)
                        field_value_pairs.append((field_name, val_str))

                # --- 2. Keyword arguments ---
                for kw in expr.keywords:
                    val_str = self.rewrite_expr(kw.value)
                    field_value_pairs.append((kw.arg, val_str))

                # --- 3. Build record string ---
                # Multi-line pretty output (for readability)
                inner = ",\n        ".join(f"{k}: {v}" for k, v in field_value_pairs)
                return "(\n        " + inner + "\n    )"

            # --- Step 3: ignore DS-types ---
            if func_name.startswith("DS"):
                raise ValueError(f"DS-type constructor should not appear in expressions: {expr}")
            

            # --- Step 4: only process interesting functions ---
            if func_name not in (quantifiers | aggregators):
                raise ValueError(f"Unsupported function call in expression: {func_name}")

            # --- Step 5: detect generator form ---
            arg = expr.args[0] if expr.args else None
            is_generator = isinstance(arg, ast.GeneratorExp)

            # --- Step 6: generator version ---
            # For example, sum(x for x in A)
            if is_generator:

                op_map = {
                    "all": " /\\ ",
                    "forall": " /\\ ",
                    "any": " \\/ ",
                    "exists": " \\/ ",
                }
                join_op = op_map[func_name]

                exprs = self.code_block.extract_generator_constraints(
                    gen=arg,
                    loop_scope=self.loop_scope
                )

                if not exprs:
                    return "true" if join_op.strip() == "/\\" else "false"

                return "(" + join_op.join(exprs) + ")"

            # --- Step 7: explicit arguments version ---
            # For example, sum([a, b, c])
            args = [self.rewrite_expr(a) for a in expr.args]

            if func_name in {"exists", "any"}:
                return "(" + " \\/ ".join(args) + ")"
            elif func_name in {"forall", "all"}:
                return "(" + " /\\ ".join(args) + ")"
            elif func_name in aggregators:
                # sum([a,b]) or max([a,b])
                return f"{func_name}({', '.join(args)})"


        elif isinstance(expr, ast.List):
            # Elements rewritten recursively so Names/Calls/etc. are handled
            elts = expr.elts
            contents = []
            dims = []
            for e in elts:
                new_content = self.rewrite_expr(e)
                dim = []
                dims.append(dim)
                contents.append(new_content)
            # Join elements with commas
            inner = ", ".join(self.rewrite_expr(e) for e in elts)
            list_str = f"[{inner}]"
            return list_str
        
        elif isinstance(expr, ast.Dict):
            # Convert Python dict literal to MiniZinc record literal
            fields = []
            for k_node, v_node in zip(expr.keys, expr.values):
                key = self.rewrite_expr(k_node)
                val = self.rewrite_expr(v_node)
                # Remove quotes if key is a string literal
                if key.startswith("'") and key.endswith("'"):
                    key = key[1:-1]
                fields.append(f"{key}: {val}")
            return "(" + ", ".join(fields) + ")"
            
        elif isinstance(expr, ast.Expression):
            return self.rewrite_expr(expr.body)

        elif isinstance(expr, str):
            return expr
        
        elif isinstance(expr, (int, float)):
            return str(expr)
        
        elif expr is None:
            return None
            

        else:
            # Fallback: use source-like syntax
            print("Fallback: use source-like syntax\n", expr, type(expr))
            return expr


def enumerate_iterable(self, iter_node):
    # range(n)
    if isinstance(iter_node, ast.Call) and iter_node.func.id == "range":
        n = self.eval_constant(iter_node.args[0])
        return [str(i) for i in range(n)]

    # constant array
    if isinstance(iter_node, ast.Name):
        name = iter_node.id
        if name in self.constant_table:
            size = self.constant_table[name]["size"]
            return [f"{name}[{i}]" for i in range(1, size + 1)]

    raise NotImplementedError(
        f"Cannot unroll generator over {ast.dump(iter_node)}"
    )


def ast_to_evaluation_constants(node: ast.AST, constant_table: Optional[dict] = None) -> dict:
    """
    Convert an AST node into a value using the constant table for name resolution.
    For example 1+ C, turns into 6 when constant_table = {'C': 5}.
    And (7 + C) * 2 turns into 24.
    """

    if constant_table is None:
        constant_table = {}

    if isinstance(node, ast.Constant):
        value = constant_table.get(node.value, node.value)
        return node.value

    elif isinstance(node, ast.Name) or isinstance(node, str):
        if isinstance(node, ast.Name):
            node = node.id

        if node in constant_table:
            value = constant_table[node].value_structure
        else:
            raise ValueError(f"Name {node} not found in constant table.")

    elif isinstance(node, ast.BinOp):
        right = ast_to_evaluation_constants(node.right, constant_table)
        left = ast_to_evaluation_constants(node.left, constant_table)
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        elif isinstance(node.op, ast.Div):
            value = left / right
        else:
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")

    elif isinstance(node, ast.UnaryOp):
        operand = ast_to_evaluation_constants(node.operand, constant_table)
        if isinstance(node.op, ast.UAdd):
            value = +operand
        elif isinstance(node.op, ast.USub):
            value = -operand
        else:
            raise TypeError(f"Unsupported unary operator: {type(node.op)}")

    elif node is None or isinstance(node, (int, float)):
        value = node

    else:
        raise TypeError(f"Unsupported AST node type for evaluation: {type(node)}, {ast.dump(node)}")
    
    if isinstance(value, str) and value.isdigit():
        if '.' in value:
            value = float(value)
        else:
            value = int(value)
    return value


### Auxiliary functions to merge with others

def ast_to_object(node: ast.AST):
    """
    Recursively convert AST literal trees (Dict, List, Tuple, Constant, BinOp, etc.)
    into actual Python objects (dicts, lists, numbers, strings, etc.).
    
    Keeps symbolic names or expressions as strings.
    """
    if node is None:
        return None
    
    if not isinstance(node, ast.AST):
        return node

    # --- Literal values ---
    if isinstance(node, ast.Constant):
        return node.value

    # --- Variable name (symbolic reference) ---
    elif isinstance(node, ast.Name):
        return node.id

    # --- Dictionary literal ---
    elif isinstance(node, ast.Dict):
        result = {}
        for k_node, v_node in zip(node.keys, node.values):
            if k_node is None:  # handle dict unpacking (**kwargs), unlikely for your DSL
                continue
            key = ast_to_object(k_node)
            val = ast_to_object(v_node)
            result[key] = val
        return result

    # --- List or tuple literal ---
    elif isinstance(node, (ast.List, ast.Tuple)):
        return [ast_to_object(e) for e in node.elts]

    # --- Binary operations (e.g. 1 + x) ---
    elif isinstance(node, ast.BinOp):
        left = ast_to_object(node.left)
        right = ast_to_object(node.right)
        op = _op_to_str(node.op)
        return f"({left} {op} {right})"

    # --- Unary operations (e.g. -x) ---
    elif isinstance(node, ast.UnaryOp):
        op = _op_to_str(node.op)
        operand = ast_to_object(node.operand)
        return f"({op}{operand})"

    # --- Attribute access (e.g. obj.field) ---
    elif isinstance(node, ast.Attribute):
        value = ast_to_object(node.value)
        return f"{value}.{node.attr}"

    # --- Function calls (e.g. f(a,b)) ---
    elif isinstance(node, ast.Call):
        func = ast_to_object(node.func)
        args = [ast_to_object(a) for a in node.args]
        return f"{func}({', '.join(map(str, args))})"

    else:
        raise TypeError(f"Unsupported AST node type: {type(node)}")
    

def _op_to_str(op):
    """Convert AST operator node to string representation."""
    if isinstance(op, ast.Add):
        return "+"
    elif isinstance(op, ast.Sub):
        return "-"
    elif isinstance(op, ast.Mult):
        return "*"
    elif isinstance(op, ast.Div):
        return "/"
    elif isinstance(op, ast.Pow):
        return "**"
    elif isinstance(op, ast.USub):
        return "-"
    elif isinstance(op, ast.UAdd):
        return "+"
    else:
        raise TypeError(f"Unsupported operator type: {type(op)}")
