import ast

# Python code to be transformed into MiniZinc
code = """
x = 0
y = 1
if x > 0:
    x = x + 1
    for t in range(1, 6):
        y = x + t
else:
    y = y + 1
    x = x + y
for t in range(1, 4):
    x = x + y + 1
    for i in range(1, 3):
        y = x + i
    y = x + 1
"""

# Parse the code into an Abstract Syntax Tree (AST)
tree = ast.parse(code)

# Tracks the current index version of each variable (e.g., x[0], x[1], ...)
variable_index = {}

# Stores the list of generated MiniZinc constraints
constraints = []

def merge_variable(var, cond_expr, idx_if, idx_else):
    merged_idx = max(idx_if, idx_else)
    variable_index[var] = merged_idx
    val_if = f"{var}[{idx_if}]"
    val_else = f"{var}[{idx_else}]"
    if_constraint = f"{var}[{merged_idx}] = {val_if};"
    else_constraint = f"{var}[{merged_idx}] = {val_else};"
    return if_constraint, else_constraint


def execute_branch(block, loop_scope, pre_index):
    global constraints, variable_index
    constraints_backup = constraints.copy()
    constraints.clear()
    variable_index = pre_index.copy()
    execute_block(block, loop_scope)
    result_constraints = constraints[:]
    result_index = variable_index.copy()
    constraints = constraints_backup
    result_constraints_without_constraint = [c.split("constraint ")[-1] for c in result_constraints]
    return result_constraints_without_constraint, result_index


# Converts a Python expression AST into a MiniZinc-compatible string
def rewrite_expr(expr, loop_scope):
    if isinstance(expr, ast.BinOp):
        # Recurse on left and right sides
        left = rewrite_expr(expr.left, loop_scope)
        right = rewrite_expr(expr.right, loop_scope)

        # Map Python AST operators to MiniZinc symbols
        op = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "div",   # Integer division
            ast.Mod: "mod",
            ast.Pow: "^"
        }.get(type(expr.op), "?")

        return f"({left} {op} {right})"

    elif isinstance(expr, ast.Name):
        name = expr.id

        # If it's a loop variable (e.g. `i` or `t`), substitute its current value
        if name in loop_scope:
            return str(loop_scope[name])

        # Otherwise, reference the most recent version of the variable
        return f"{name}[{variable_index.get(name, 0)}]"

    elif isinstance(expr, ast.Constant):
        return str(expr.value)

    else:
        # Fallback for unsupported nodes
        # raise ValueError(f"Unsupported expression type: {type(expr)}")
        return ast.unparse(expr)

# Recursively execute a block of statements, updating the symbolic state
def execute_block(block, loop_scope):
    for stmt in block:
        
        print("Expression: ", ast.unparse(stmt))
        print("Type: ", type(stmt))

        # Handle assignments: e.g., x = x + y
        if isinstance(stmt, ast.Assign):
            var = stmt.targets[0].id
            rhs = rewrite_expr(stmt.value, loop_scope)

            # Update variable version index
            idx = variable_index.get(var, 0) + 1
            variable_index[var] = idx

            # Add MiniZinc constraint
            constraints.append(f"constraint {var}[{idx}] = {rhs};")

        # Handle for-loops (possibly nested)
        elif isinstance(stmt, ast.For):
            loop_var = stmt.target.id

            # Extract loop bounds (assumes range(start, end))
            start = stmt.iter.args[0].value
            end = stmt.iter.args[1].value

            # Simulate each iteration
            for v in range(start, end):
                new_scope = loop_scope.copy()
                new_scope[loop_var] = v  # Track current value of loop variable
                execute_block(stmt.body, new_scope)  # Recurse on body

        elif isinstance(stmt, ast.If):
            cond_expr = rewrite_expr(stmt.test, loop_scope)
            pre_branch_index = variable_index.copy()

            # Run both branches
            branch_if_constraints, index_after_if = execute_branch(stmt.body, loop_scope, pre_branch_index)
            branch_else_constraints, index_after_else = execute_branch(stmt.orelse or [], loop_scope, pre_branch_index)

            # Merge all variables that changed
            all_vars = set(index_after_if) | set(index_after_else)
            for var in all_vars:
                idx_before = pre_branch_index.get(var, 0)
                idx_if = index_after_if.get(var, idx_before)
                idx_else = index_after_else.get(var, idx_before)
                if_constraint, else_constraint = merge_variable(var, cond_expr, idx_if, idx_else)
                branch_if_constraints.append(if_constraint)
                branch_else_constraints.append(else_constraint)

            constraints.extend([
                f"constraint {cond_expr} -> {constr}" for constr in branch_if_constraints
            ])
            constraints.extend([
                f"constraint not {cond_expr} -> {constr}" for constr in branch_else_constraints
            ])


execute_block(tree.body, {})

# Determine the max index to define the length of variable arrays
max_index = max(variable_index.values())

# Declare MiniZinc arrays for each variable
decls = [f"array[0..{max_index}] of var int: {var};" for var in variable_index]

# Print the full MiniZinc model
print("\n".join(decls + constraints + ["solve satisfy;"]))
