import ast
from typing import Optional


minizinc_original_types = {
    "int",
    "float",
    "string",
    "bool",
}


def ast_to_evaluation_constants(node: ast.AST, constant_table: Optional[dict] = None) -> dict:
    """
    Convert an AST node into a value using the constant table for name resolution.
    For example 1+ C, turns into 6 when constant_table = {'C': 5}.
    And (7 + C) * 2 turns into 24.
    """

    if constant_table is None:
        constant_table = {}

    if isinstance(node, ast.Constant):
        print("looking for Constant:", node.value)
        return constant_table.get(node.value, node.value)
        return node.value

    elif isinstance(node, ast.Name):
        if node.id in constant_table:
            return constant_table[node.id].value_structure
        else:
            raise ValueError(f"Name {node.id} not found in constant table.")

    elif isinstance(node, ast.BinOp):
        right = ast_to_evaluation_constants(node.right, constant_table)
        print("Right:", ast.dump(node.right) if isinstance(node.right, ast.AST) else node.right)
        left = ast_to_evaluation_constants(node.left, constant_table)
        print("Left:", ast.dump(node.left) if isinstance(node.left, ast.AST) else node.left, " Right:", ast.dump(node.right) if isinstance(node.right, ast.AST) else node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right
        else:
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")

    elif isinstance(node, ast.UnaryOp):
        operand = ast_to_evaluation_constants(node.operand, constant_table)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        else:
            raise TypeError(f"Unsupported unary operator: {type(node.op)}")
        
    elif node is None or isinstance(node, ast.AST) is False:
        return node

    else:
        raise TypeError(f"Unsupported AST node type for evaluation: {type(node)}")


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