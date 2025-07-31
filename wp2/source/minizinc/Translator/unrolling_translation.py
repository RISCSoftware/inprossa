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
PIECES = [2,5,3,1,9,5,3,2]
depth = 0
length = 0
n_length = 0
n_prev_layer = 0
new_beam = True
for piece in PIECES:
    length = length + piece
    n_length = n_length + 1
    assert length <= MAX_LENGTH
    if length == MAX_LENGTH:
        depth = depth + 1
        n_prev_layer = n_length
        n_length = 0
        length = 0
        if depth == MAX_DEPTH:
            new_beam = True
            depth = 0
    else:
        new_beam = False
        for i in range(1, MAX_N_LENGTH):
            if i < n_prev_layer:
                start = current_index - n_length - n_prev_layer + 1
                end = start + i - 1
                s = 0
                for j in range(1, MAX_N_LENGTH):
                    if j >= start and j <= end:
                        s = s + PIECES[j]
                assert (s - length) >= MIN_DIST
                assert (length - s) >= MIN_DIST
"""

# Parse the code into an Abstract Syntax Tree (AST)
tree = ast.parse(code_check_machine)

# Tracks the current version (index) of each variable (e.g., x[0], x[1], ...)
variable_index = {}

# Tracks the set of constant (symbolic) names, identified by being all uppercase
symbol_table = {}
is_constant = set()


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


# List of accumulated constraints generated during symbolic execution
constraints = []


# Merges variable versions after an if-else branch by creating a new unified version
def merge_variable(var, idx_if, idx_else):
    merged_idx = max(idx_if, idx_else)
    variable_index[var] = merged_idx
    if_constraint = Constraint(f"{var}[{merged_idx}] = {var}[{idx_if}]")
    else_constraint = Constraint(f"{var}[{merged_idx}] = {var}[{idx_else}]")
    return if_constraint, else_constraint


# Executes a code block (body of if or else) independently and returns resulting state
def execute_branch(block, loop_scope, pre_index):
    global constraints, variable_index
    constraints_backup = constraints.copy()
    constraints.clear()
    variable_index = pre_index.copy()
    execute_block(block, loop_scope)
    result_constraints = constraints[:]
    result_index = variable_index.copy()
    constraints = constraints_backup
    return result_constraints, result_index


# Converts a Python expression AST into a MiniZinc-compatible string
def rewrite_expr(expr, loop_scope):
    if isinstance(expr, ast.BinOp):
        # Handle binary operations like x + y
        left = rewrite_expr(expr.left, loop_scope)
        right = rewrite_expr(expr.right, loop_scope)
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
        left = rewrite_expr(expr.left, loop_scope)
        right = rewrite_expr(expr.comparators[0], loop_scope)
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
        values = [rewrite_expr(v, loop_scope) for v in expr.values]
        return f"({' {} '.format(op).join(values)})"

    elif isinstance(expr, ast.Name):
        name = expr.id
        # Loop variable
        if name in loop_scope:
            return str(loop_scope[name])
        # Constant (e.g., MAX_LENGTH)
        if name.isupper():
            is_constant.add(name)
            return name
        # Evolving variable: versioned reference
        return f"{name}[{variable_index.get(name, 0)}]"

    elif isinstance(expr, ast.Constant):
        # Handle literals: numbers, booleans
        return str(expr.value)

    else:
        # Fallback: use source-like syntax
        return ast.unparse(expr)


# Recursively execute a block of Python statements, updating symbolic state
def execute_block(block, loop_scope):
    for stmt in block:
        print("Expression: ", ast.unparse(stmt))
        print("Type: ", type(stmt))

        # Handle assignment statements
        if isinstance(stmt, ast.Assign):
            var = stmt.targets[0].id

            # Detect and record constant definitions (uppercase names)
            if var.isupper():
                if isinstance(stmt.value, ast.Constant):
                    symbol_table[var] = stmt.value.value
                elif isinstance(stmt.value, ast.List):
                    symbol_table[var] = [elt.value for elt in stmt.value.elts]
                is_constant.add(var)
                continue  # Don't emit constraint for constants

            # For evolving variables, emit a versioned constraint
            rhs = rewrite_expr(stmt.value, loop_scope)
            idx = variable_index.get(var, 0) + 1
            variable_index[var] = idx
            constraints.append(Constraint(f"{var}[{idx}] = {rhs}"))

        # Handle for-loops, including range and enumerate
        elif isinstance(stmt, ast.For):
            iter_values = []

            # Case 1: range(start, end)
            if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
                func_id = stmt.iter.func.id

                # range(start, end)
                if func_id == "range":
                    print("stmt.iter.args: ", [ast.unparse(arg) for arg in stmt.iter.args])
                    start_node = stmt.iter.args[0]
                    end_node = stmt.iter.args[1]

                    # Evaluate start
                    if isinstance(start_node, ast.Constant):
                        start_val = start_node.value
                    elif isinstance(start_node, ast.Name) and start_node.id in symbol_table:
                        start_val = symbol_table[start_node.id]
                    else:
                        raise ValueError(f"Unsupported start in range: {ast.unparse(start_node)}")

                    # Evaluate end
                    if isinstance(end_node, ast.Constant):
                        end_val = end_node.value
                    elif isinstance(end_node, ast.Name) and end_node.id in symbol_table:
                        end_val = symbol_table[end_node.id]
                    else:
                        raise ValueError(f"Unsupported end in range: {ast.unparse(end_node)}")

                    # Now unroll the loop using resolved values
                    iter_values = list(range(start_val, end_val))
                    loop_vars = [stmt.target.id]

                # enumerate([...]) or enumerate(PIECES)
                elif func_id == "enumerate":
                    arg = stmt.iter.args[0]

                    # enumerate over list literal
                    if isinstance(arg, ast.List):
                        values = [elt.value for elt in arg.elts]
                    # enumerate over constant array like PIECES
                    elif isinstance(arg, ast.Name) and arg.id in symbol_table:
                        values = symbol_table[arg.id]
                    else:
                        raise ValueError(f"Unsupported enumerate argument: {ast.unparse(arg)}")

                    iter_values = list(enumerate(values))
                    loop_vars = [elt.id for elt in stmt.target.elts]  # e.g. for i, x in enumerate(...)

                else:
                    raise ValueError(f"Unsupported function call iterator: {ast.unparse(stmt.iter)}")

            # Case 2: iterate over list literal: for x in [1, 2, 3]
            elif isinstance(stmt.iter, ast.List):
                iter_values = [elt.value for elt in stmt.iter.elts]
                loop_vars = [stmt.target.id]

            # Case 3: iterate over constant name: for x in PIECES
            elif isinstance(stmt.iter, ast.Name):
                const_name = stmt.iter.id
                if const_name in symbol_table:
                    iter_values = symbol_table[const_name]
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
                    for name, val in zip(loop_vars, item):
                        new_scope[name] = val
                else:
                    new_scope[loop_vars[0]] = item
                execute_block(stmt.body, new_scope)


        # Handle if-statements with symbolic branching
        elif isinstance(stmt, ast.If):
            cond_expr = rewrite_expr(stmt.test, loop_scope)
            pre_branch_index = variable_index.copy()

            # Run both if and else branches independently
            branch_if_constraints, index_after_if = execute_branch(stmt.body, loop_scope, pre_branch_index)
            branch_else_constraints, index_after_else = execute_branch(stmt.orelse or [], loop_scope, pre_branch_index)

            # Merge variable versions from both branches
            all_vars = set(index_after_if) | set(index_after_else)
            for var in all_vars:
                idx_before = pre_branch_index.get(var, 0)
                idx_if = index_after_if.get(var, idx_before)
                idx_else = index_after_else.get(var, idx_before)
                if_constraint, else_constraint = merge_variable(var, idx_if, idx_else)
                branch_if_constraints.append(if_constraint)
                branch_else_constraints.append(else_constraint)

            # Add conditional constraints for both branches
            constraints.extend([
                Constraint(c.expression, c.conditions + [cond_expr])
                for c in branch_if_constraints
            ])
            constraints.extend([
                Constraint(c.expression, c.conditions + [f"(not {cond_expr})"])
                for c in branch_else_constraints
            ])

        # Handle assert statements
        elif isinstance(stmt, ast.Assert):
            test_expr = rewrite_expr(stmt.test, loop_scope)
            constraints.append(Constraint(test_expr))


# Execute the full AST with an empty initial scope
execute_block(tree.body, {})

# Declare constants as MiniZinc symbols (not versioned)
symbol_decls = []
for name, val in symbol_table.items():
    if isinstance(val, int):
        symbol_decls.append(f"int: {name} = {val};")
    elif isinstance(val, list):
        symbol_decls.append(f"array[0..{len(val)-1}] of int: {name} = [{', '.join(map(str, val))}];")

# Declare variables as arrays of versioned values
decls = [f"array[0..{variable_index[var]}] of var int: {var};"
         for var in variable_index]

# Combine constraints into MiniZinc syntax
text_constraints = [str(c) for c in constraints if c is not None]

# Output the final MiniZinc model
print("\n".join(symbol_decls + decls + text_constraints + ["solve satisfy;"]))
