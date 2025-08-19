import ast

# Python code to be transformed into MiniZinc
code = """
x = 0
y = 1
if x > 0:
    x = x + 1
    if y < 5:
        y = y + 1
    for t in range(1, 6):
        y = x + t
        assert y > x and y < 10 + t
else:
    y = y + 1
    x = x + y
for i, t in enumerate([455,1,255]):
    x = x + y + 1
    for j in range(1, 3):
        y = x + j
    y = x + 1 + t + i
"""

# FORBIDDEN_INTERVALS = [[3,4], [7,8]]
# Python code to be transformed into MiniZinc
code_check_machine = """
MAX_LENGTH = 10
MAX_DEPTH = 5
MAX_N_LENGTH = 5
MIN_DIST = 1
PIECES = [2,5,3,1,9,5,3,2] # 
depth = 0
length = 0
n_length = 0
n_prev_layer = 0
new_beam = 1
for current_index, piece in enumerate(PIECES):
    length = length + piece
    n_length = n_length + 1
    assert length <= MAX_LENGTH
    if length == MAX_LENGTH:
        depth = depth + 1
        n_prev_layer = n_length
        n_length = 0
        length = 0
        # if depth == MAX_DEPTH:
        #     new_beam = 1
        #     depth = 0
    else:
        # if new_beam != 1:
            for i in range(1, MAX_N_LENGTH):
                if i < n_prev_layer:
                    start = current_index - n_length - n_prev_layer + 1
                    end = start + i - 1
                    s = 0
                    for j in range(1, MAX_N_LENGTH):
                        # right now, we need to do the for in this way
                        # in  the future we can do range(start, end + 1)
                        # if we know lower and upper bounds for start and end
                        if j >= start and j <= end:
                            s = s + PIECES[j]
                    assert abs(s - length) >= MIN_DIST
        # new_beam = 0
"""


# Class to represent a MiniZinc constraint, with optional conditional guards
class Constraint:
    def __init__(self, expression="", conditions=[]):
        self.conditions = conditions
        self.expression = expression

    def add_condition(self, condition):
        self.conditions.append(condition)
        return self

    def __str__(self):
        if self.conditions == []:
            return f"constraint {self.expression};"
        else:
            # Join conditions with '/\' (and) for MiniZinc syntax
            conditions_str = " /\\ ".join(self.conditions)
            return f"constraint {conditions_str} -> {self.expression};"


class MiniZincTranslator:
    def __init__(self, code):
        # Tracks the current version (index)
        # of each variable (e.g., x[0], x[1], ...)
        self.variable_index = {}
        # Tracks the variable declarations
        # varname → (type, domain), e.g. ('float', None)
        self.variable_declarations = {}
        # Tracks the set of constant (symbolic) names,
        # identified by being all uppercase
        self.symbol_table = {}
        self.is_constant = set()
        # List of accumulated constraints generated during symbolic execution
        self.constraints = []
        self.code = code

    def unroll_translation(self):

        # Parse the code into an Abstract Syntax Tree (AST)
        tree = ast.parse(self.code)

        # Execute the full AST with an empty initial scope
        self.execute_block(tree.body, {})

        # Declare constants as MiniZinc symbols (not versioned)
        symbol_decls = []
        for name, val in self.symbol_table.items():
            if isinstance(val, int):
                symbol_decls.append(f"int: {name} = {val};")
            elif isinstance(val, list):
                symbol_decls.append(f"array[1..{len(val)}] of int: {name} = [{', '.join(map(str, val))}];")

        # Declare variables as arrays of versioned values
        decls = []
        for var, size in self.variable_index.items():
            var_type, domain = self.variable_declarations.get(var, ("int", None))  # default int if explicitly assigned
            if domain:
                decls.append(f"array[1..{size}] of var {var_type}:{domain}: {var};")
            else:
                decls.append(f"array[1..{size}] of var {var_type}: {var};")


        # Combine constraints into MiniZinc syntax
        text_constraints = [str(c) for c in self.constraints if c is not None]

        # Output the final MiniZinc model
        minizinc_code = "\n".join(symbol_decls + decls + text_constraints + ["solve satisfy;"])
        return minizinc_code

    # Merges variable versions after an if-else branch
    # by creating a new unified version
    def merge_variable(self, var, idx_if, idx_else):
        merged_idx = max(idx_if, idx_else)
        self.variable_index[var] = merged_idx
        constraints = dict()

        if idx_if != merged_idx:
            if idx_if == 0:
                # If the variable was not assigned in the if-branch,
                # we can use a special UNDEFINED value
                # self.symbol_table["UNDEFINED"] = -99999
                # constraints["if"] = Constraint(f"{var}[{merged_idx}] = UNDEFINED")
                print(f"Warning: Variable '{var}' not assigned in if-branch") #; using UNDEFINED.")
            else:
                constraints["if"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_if}]")

        if idx_else != merged_idx:
            if idx_else == 0:
                # If the variable was not assigned in the else-branch,
                # we can use a special UNDEFINED value
                # self.symbol_table["UNDEFINED"] = -99999
                # constraints["else"] = Constraint(f"{var}[{merged_idx}] = UNDEFINED")
                print(f"Warning: Variable '{var}' not assigned in else-branch") #; using UNDEFINED.")
            else:
                constraints["else"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_else}]")

        return constraints

    # Executes a code block (body of if or else) independently
    # and returns resulting state
    def execute_branch(self, block, loop_scope, pre_index):
        constraints_backup = self.constraints.copy()
        self.constraints.clear()
        self.variable_index = pre_index.copy()
        self.execute_block(block, loop_scope)
        result_constraints = self.constraints[:]
        result_index = self.variable_index.copy()
        self.constraints = constraints_backup
        return result_constraints, result_index

    # Converts a Python expression AST into a MiniZinc-compatible string
    def rewrite_expr(self, expr, loop_scope):
        if isinstance(expr, ast.BinOp):
            # Handle binary operations like x + y
            left = self.rewrite_expr(expr.left, loop_scope)
            right = self.rewrite_expr(expr.right, loop_scope)
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
            left = self.rewrite_expr(expr.left, loop_scope)
            right = self.rewrite_expr(expr.comparators[0], loop_scope)
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
                ast.And: "/\\",
                ast.Or: "\\/"
            }.get(type(expr.op), "?")
            values = [self.rewrite_expr(v, loop_scope) for v in expr.values]
            return f"({' {} '.format(op).join(values)})"

        elif isinstance(expr, ast.Name):
            name = expr.id

            # Loop variable
            if name in loop_scope:
                return str(loop_scope[name])

            # Constant (e.g., MAX_LENGTH)
            if name.isupper():
                self.is_constant.add(name)
                return name

            # Not constant, not loop var — must be a normal variable
            if name not in self.variable_index:
                # First-time reference (e.g., used in an expression before assignment)
                print(f"Warning: Variable '{name}' used without assignment: assuming type 'float'")
                self.variable_index[name] = 1
                self.variable_declarations[name] = ("float", None)  # default type: float

            return f"{name}[{self.variable_index[name]}]"

        elif isinstance(expr, ast.Constant):
            # Handle literals: numbers, booleans
            return str(expr.value)

        elif isinstance(expr, ast.Subscript):
            # Handle array access like VALUES[i]
            base = self.rewrite_expr(expr.value, loop_scope)

            # Get the index expression, which can be a Name, Constant, or BinOp
            if isinstance(expr.slice, ast.Index):  # for Python <3.9
                index = expr.slice.value
            else:  # for Python 3.9+
                index = expr.slice

            index_str = self.rewrite_expr(index, loop_scope)
            return f"{base}[{index_str}]"

        elif isinstance(expr, ast.Call):
            func_name = expr.func.id if isinstance(expr.func, ast.Name) else ast.unparse(expr.func)

            # Only support known functions like abs, max, min
            if func_name in {"abs", "max", "min"}:
                args = [self.rewrite_expr(arg, loop_scope) for arg in expr.args]
                return f"{func_name}({', '.join(args)})"
            else:
                raise ValueError(f"Unsupported function call: {func_name}")

        else:
            # Fallback: use source-like syntax
            return ast.unparse(expr)

    # Recursively execute a block of Python statements, updating symbolic state
    def execute_block(self, block, loop_scope):
        for stmt in block:
            # Handle assignment statements
            if isinstance(stmt, ast.Assign):
                var = stmt.targets[0].id

                # Detect and record constant definitions (uppercase names)
                if var.isupper():
                    if isinstance(stmt.value, ast.Constant):
                        self.symbol_table[var] = stmt.value.value
                    elif isinstance(stmt.value, ast.List):
                        self.symbol_table[var] = [elt.value for elt in stmt.value.elts]
                    self.is_constant.add(var)
                    continue  # Don't emit constraint for constants

                # For evolving variables, emit a versioned constraint
                rhs = self.rewrite_expr(stmt.value, loop_scope)
                idx = self.variable_index.get(var, 0) + 1
                self.variable_index[var] = idx
                self.constraints.append(Constraint(f"{var}[{idx}] = {rhs}"))

            # Handle for-loops, including range and enumerate
            elif isinstance(stmt, ast.For):
                iter_values = []

                # Case 1: range(start, end)
                if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
                    func_id = stmt.iter.func.id

                    # range(start, end)
                    if func_id == "range":
                        start_node = stmt.iter.args[0]
                        end_node = stmt.iter.args[1]

                        # Evaluate start
                        if isinstance(start_node, ast.Constant):
                            start_val = start_node.value
                        elif isinstance(start_node, ast.Name) and start_node.id in self.symbol_table:
                            start_val = self.symbol_table[start_node.id]
                        else:
                            raise ValueError(f"Unsupported start in range: {ast.unparse(start_node)}")

                        # Evaluate end
                        if isinstance(end_node, ast.Constant):
                            end_val = end_node.value
                        elif isinstance(end_node, ast.Name) and end_node.id in self.symbol_table:
                            end_val = self.symbol_table[end_node.id]
                        else:
                            raise ValueError(f"Unsupported end in range: {ast.unparse(end_node)}")

                        # Now unroll the loop using resolved values
                        iter_values = list(range(start_val, end_val))
                        loop_vars = [stmt.target.id]

                    # enumerate([...]) or enumerate(PIECES)
                    # e.g. PIECES = [2, 5, 3]
                    # for current_index, piece in enumerate(PIECES):
                    elif func_id == "enumerate":
                        arg = stmt.iter.args[0]

                        # enumerate over list literal
                        if isinstance(arg, ast.List):
                            values = [elt.value for elt in arg.elts]
                        # enumerate over constant array like PIECES
                        elif isinstance(arg, ast.Name) and arg.id in self.symbol_table:
                            values = self.symbol_table[arg.id]
                        else:
                            raise ValueError(f"Unsupported enumerate argument: {ast.unparse(arg)}")

                        iter_values = list(enumerate(values, start=1))
                        # iter_values: [(1, 2), (2, 5), (3, 3)]
                        loop_vars = [elt.id for elt in stmt.target.elts]
                        # loop_vars: ['current_index', 'piece']

                    else:
                        raise ValueError(f"Unsupported function call iterator: {ast.unparse(stmt.iter)}")

                # Case 2: iterate over list literal: for x in [1, 2, 3]
                elif isinstance(stmt.iter, ast.List):
                    iter_values = [elt.value for elt in stmt.iter.elts]
                    loop_vars = [stmt.target.id]

                # Case 3: iterate over constant name: for x in PIECES
                elif isinstance(stmt.iter, ast.Name):
                    const_name = stmt.iter.id
                    if const_name in self.symbol_table:
                        iter_values = [f"{const_name}[{i}]" for i in range(1, len(self.symbol_table[const_name]) + 1)]
                        loop_vars = [stmt.target.id]
                    else:
                        raise ValueError(f"Unknown constant array: {const_name}")

                # Anything else is unsupported
                else:
                    raise ValueError(f"Unsupported loop iterator: {ast.unparse(stmt.iter)}")

                # Iterate through values and execute body with updated loop variable bindings
                for item in iter_values:
                    new_scope = loop_scope.copy()
                    if isinstance(item, tuple):
                        # enumerate(array): item = (index, value)
                        index_val = item[0]
                        array_name = stmt.iter.args[0].id if isinstance(stmt.iter.args[0], ast.Name) else None
                        index_var, element_var = loop_vars
                        new_scope[index_var] = index_val
                        new_scope[element_var] = f"{array_name}[{index_val}]"
                    else:
                        # for x in ARRAY or for x in [list]
                        array_name = stmt.iter.id if isinstance(stmt.iter, ast.Name) else None
                        loop_var = loop_vars[0]
                        index_val = iter_values.index(item) + 1
                        if array_name is None: # For constants
                            new_scope[loop_var] = index_val
                        else:
                            new_scope[loop_var] = f"{array_name}[{index_val}]"
                    self.execute_block(stmt.body, new_scope)

            # Handle if-statements with symbolic branching
            elif isinstance(stmt, ast.If):
                cond_expr = self.rewrite_expr(stmt.test, loop_scope)
                pre_branch_index = self.variable_index.copy()

                # Run both if and else branches independently
                branch_if_constraints, index_after_if = self.execute_branch(stmt.body, loop_scope, pre_branch_index)
                branch_else_constraints, index_after_else = self.execute_branch(stmt.orelse or [], loop_scope, pre_branch_index)

                # Merge variable versions from both branches
                all_vars = set(index_after_if) | set(index_after_else)
                for var in all_vars:
                    idx_before = pre_branch_index.get(var, 0)
                    idx_if = index_after_if.get(var, idx_before)
                    idx_else = index_after_else.get(var, idx_before)
                    constraints = self.merge_variable(var, idx_if, idx_else)
                    if "if" in constraints:
                        branch_if_constraints.append(constraints["if"])
                    if "else" in constraints:
                        branch_else_constraints.append(constraints["else"])

                # Add conditional constraints for both branches
                self.constraints.extend([
                    Constraint(c.expression, c.conditions + [cond_expr])
                    for c in branch_if_constraints
                ])
                self.constraints.extend([
                    Constraint(c.expression, c.conditions + [f"(not {cond_expr})"])
                    for c in branch_else_constraints
                ])

            # Handle assert statements
            elif isinstance(stmt, ast.Assert):
                test_expr = self.rewrite_expr(stmt.test, loop_scope)
                self.constraints.append(Constraint(test_expr))


if __name__ == "__main__":
    # Test the MiniZinc translation with the provided code
    translator = MiniZincTranslator(code_check_machine)
    print(translator.unroll_translation())
