import ast
from typing import Union
from Translator.Objects.DSTypes import DSList, DSRecord


class Constant:
    def __init__(self,
                 name: str,
                 stmt_value: str = None,
                 type_: Union[int, float, bool, DSList] = "int",
                 code_block=None,
                 loop_scope=None):
        self.code_block = code_block
        self.name = name
        self.type = type_
        self.loop_scope = {} if loop_scope is None else loop_scope
        empty_structure = self.build_empty_structure(self.type)
        print("Empty structure for", self.name, ":", empty_structure)
        print("DSType:", self.type)
        self.value_structure = self.fill_structure(
            empty_structure,
            stmt_value)
        print("Filled structure for", self.name, ":", self.value_structure)


    def to_minizinc(self) -> str:
        return f"{self.type.name}: {self.name} = {self._to_mzn(self.value_structure)}"

    def _to_mzn(self, value):
        """Recursively convert stored Python structures to MiniZinc text."""
        print("Converting to MZN:", ast.dump(value, indent=4) if isinstance(value, ast.AST) else value)
        if isinstance(value, dict):
            fields = [f"{k}: {self._to_mzn(v)}" for k, v in value.items()]
            return f"({', '.join(fields)})"
        elif isinstance(value, (list, tuple)):
            elems = [f"{self._to_mzn(v)}" for v in value]
            return f"[{', '.join(elems)}]"
        elif isinstance(value, str):
            return f"{value}"
        else:
            return str(value)

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

    def build_empty_structure(self, ds_type):
        """
        Build a Python structure matching the DS type shape.
        DSRecord -> dict of fields
        DSList   -> list of elements
        Base types -> None
        """

        if isinstance(ds_type, DSRecord):
            return {k: self.build_empty_structure(v) for k, v in ds_type.types_dict.items()}
        elif isinstance(ds_type, DSList):  # DSList
            return [self.build_empty_structure(ds_type.elem_type) for _ in range(ds_type.length)]
        else:
            return None

    def fill_structure(self, target, value_node):
        """
        Recursively fill a pre-built DSRecord/DSList structure (target)
        from an AST node representing dicts/lists/constants.
        """
        # --- 1. Dicts: e.g. {"x":1,"y":2}
        if isinstance(value_node, ast.Dict):
            for key_node, val_node in zip(value_node.keys, value_node.values):
                # extract key name (must be str constant or name)
                if isinstance(key_node, ast.Constant):
                    key = key_node.value
                elif isinstance(key_node, ast.Name):
                    key = key_node.id
                else:
                    raise TypeError(f"Unsupported dict key type: {type(key_node)}")

                if isinstance(target, dict) and key in target:
                    target[key] = self.fill_structure(target[key], val_node)
            return target

        # --- 2. Lists or tuples: e.g. [1,2,3] or [(x:1), (x:2)]
        elif isinstance(value_node, (ast.List, ast.Tuple)):
            if not isinstance(target, list):
                raise TypeError("Expected list target for list AST node")
            for i, elem_node in enumerate(value_node.elts):
                if i < len(target):
                    target[i] = self.fill_structure(target[i], elem_node)
            return target
        # --- 3. Constants or other expressions
        else:
            return self.code_block.rewrite_expr(value_node, loop_scope=self.loop_scope)
        
    def from_stmt_value_to_value(self, stmt_value):
        """Process the stmt_value AST to compute the actual value."""
        if stmt_value is not None:
            try:
                # Substitute known constants before evaluation
                tree = self.substitute_constants(stmt_value, self.code_block.constant_table)

                # Try evaluating the AST directly (safe subset)
                evaluated = self.safe_eval(tree)

                # rewrite_expr if not purely evaluable
                if evaluated is None:
                    rewritten = self.code_block.rewrite_expr(tree, get_numeral=True, loop_scope=self.loop_scope)
                    evaluated = self.to_number(rewritten)

                return evaluated
            except Exception as e:
                # fallback if not evaluable
                return stmt_value

#     def assign_chain(self, structure, chain, value):
#         """
#         Recursively assign `value` into a nested structure (dict/list)
#         following a key/index chain where each step is a tuple:
#             ("dict", key)  or  ("list", index)
        
#         Supports partial record updates like:
#             assign_chain(fam, [("dict","father")], {"name":"Peter","age":23})
#             assign_chain(fam, [("dict","children"),("list",1),("dict","age")], 12)
#         """
#         if isinstance(value, ast.Tuple):
#             print("Converting tuple to dict for assignment:", value)
#             print("Dump:", ast.dump(value, indent=4))
#             value = value.elts[0]
#         if isinstance(value, (ast.List, ast.Dict)):
#             value = ast_to_object(value)
#         if not chain:
#             # merge or overwrite directly
#             if isinstance(structure, dict) and isinstance(value, dict):
#                 for k, v in value.items():
#                     self.assign_chain(structure, [("dict", k)], v)
#             elif isinstance(structure, list) and isinstance(value, list):
#                 for i, v in enumerate(value):
#                     if i < len(structure):
#                         self.assign_chain(structure, [("list", i)], v)
#             else:
#                 return value
#             return structure

#         (kind, key), *rest = chain
#         print("Assigning chain step:", kind, key, "Rest:", rest, "Current structure:", structure)
#         print("Value to assign:", value)

#         # descend into substructure
#         if kind == "dict":
#             if not isinstance(structure, dict):
#                 raise TypeError(f"Expected dict at this step, got {type(structure)}")
#             if key not in structure:
#                 structure[key] = {} if rest else None
#             print("Before recursive assign:", structure[key])
#             structure[key] = self.assign_chain(structure[key], rest, value)

#         elif kind == "list":
#             if not isinstance(structure, list):
#                 raise TypeError(f"Expected list at this step, got {type(structure)}")
#             if key >= len(structure):
#                 raise IndexError(f"List index {key} out of range (len={len(structure)})")
#             print("Before recursive assign:", structure[key])
#             structure[key] = self.assign_chain(structure[key], rest, value)

#         else:
#             raise ValueError(f"Invalid chain kind: {kind}")

#         return structure




# ### Auxiliary functions to merge with others

def ast_to_object(node):
    """
    Recursively convert AST literal trees (Dict, List, Tuple, Constant, BinOp, etc.)
    into actual Python objects (dicts, lists, numbers, strings, etc.).
    
    Keeps symbolic names or expressions as strings.
    """
    if node is None:
        return None

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