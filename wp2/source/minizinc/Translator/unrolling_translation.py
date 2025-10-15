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
code = """
def cutting(length, cut1, cut2):
    len1 = cut1
    len2 = cut2 - cut1
    len3 = length - cut2
    return len1, len2, len3

len1, len2, len3 = cutting(10, 2, 5)
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
        self.code = code

    def extract_functions_to_predicates(self):
        """
        Extracts functions from the provided Python code.
        This method should parse the code and identify function definitions
        that can be translated into MiniZinc predicates.
        """
        # Parse the code into an Abstract Syntax Tree (AST)
        tree = ast.parse(self.code)
        functions = {}
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                func_name = stmt.name
                args = [arg.arg for arg in stmt.args.args]
                functions[func_name] = (args, stmt.body)

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
    

class CodeBlock:
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
                # print(f"Warning: Variable '{name}' used without assignment: assuming type 'float'")
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

    def execute_block_assign(self, stmt, loop_scope):

        var = stmt.targets[0].id

        # Detect and record constant definitions (uppercase names)
        if var.isupper():
            if isinstance(stmt.value, ast.Constant):
                self.symbol_table[var] = stmt.value.value
            elif isinstance(stmt.value, ast.List):
                self.symbol_table[var] = [elt.value for elt in stmt.value.elts]
            self.is_constant.add(var)
            return  # Don't emit constraint for constants

        # For evolving variables, emit a versioned constraint
        rhs = self.rewrite_expr(stmt.value, loop_scope)
        idx = self.variable_index.get(var, 0) + 1
        self.variable_index[var] = idx
        self.constraints.append(Constraint(f"{var}[{idx}] = {rhs}"))

    def _resolve_range_iter(self, stmt):
        # range(start, end)
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
        return iter_values, loop_vars

    def _resolve_enumerate_iter(self, stmt):
        # enumerate([...]) or enumerate(PIECES)
        # e.g. PIECES = [2, 5, 3]
        # for current_index, piece in enumerate(PIECES):
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
        return iter_values, loop_vars

    def execute_block_for(self, stmt, loop_scope):
        iter_values = []
        loop_vars = []

        # Case 1: call-based iterables (range, enumerate)
        if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
            func_id = stmt.iter.func.id

            if func_id == "range":
                # range(start, end)
                iter_values, loop_vars = self._resolve_range_iter(stmt)

            elif func_id == "enumerate":
                # enumerate([...]) or enumerate(PIECES)
                # e.g. PIECES = [2, 5, 3]
                # for current_index, piece in enumerate(PIECES):
                iter_values, loop_vars = self._resolve_enumerate_iter(stmt)

            else:
                raise ValueError(f"Unsupported function call iterator: {ast.unparse(stmt.iter)}")

        # Case 2: list literal
        elif isinstance(stmt.iter, ast.List):
            iter_values = [elt.value for elt in stmt.iter.elts]  # literal values
            loop_vars = [stmt.target.id]

        # Case 3: constant name
        elif isinstance(stmt.iter, ast.Name):
            const_name = stmt.iter.id
            if const_name in self.symbol_table:
                # Keep symbolic reference (CONST[i]) to preserve constraints
                iter_values = [f"{const_name}[{i}]" for i in range(1, len(self.symbol_table[const_name]) + 1)]
                loop_vars = [stmt.target.id]
            else:
                raise ValueError(f"Unknown constant array: {const_name}")

        else:
            raise ValueError(f"Unsupported loop iterator: {ast.unparse(stmt.iter)}")

        # Execute body with bound loop variables
        for item in iter_values:
            new_scope = loop_scope.copy()

            if isinstance(item, tuple):
                # enumerate(...): (index, element_value)
                index_val, element_val = item
                index_var, element_var = loop_vars

                # Determine if enumerate(NAME) or enumerate([…])
                arg0 = stmt.iter.args[0]
                array_name = arg0.id if (isinstance(stmt.iter, ast.Call)
                                        and isinstance(stmt.iter.func, ast.Name)
                                        and stmt.iter.func.id == "enumerate"
                                        and isinstance(arg0, ast.Name)) else None

                new_scope[index_var] = index_val
                if array_name:
                    # symbolic element for constant array
                    new_scope[element_var] = f"{array_name}[{index_val}]"
                else:
                    # literal element for list literal
                    new_scope[element_var] = element_val

            else:
                # Non-enumerate: either CONST array (symbolic) or list literal (value)
                loop_var = loop_vars[0]
                if isinstance(stmt.iter, ast.Name):
                    array_name = stmt.iter.id
                    index_val = iter_values.index(item) + 1
                    new_scope[loop_var] = f"{array_name}[{index_val}]"
                else:
                    # list literal → bind the actual value
                    new_scope[loop_var] = item

            self.execute_block(stmt.body, new_scope)

    def execute_block_if(self, stmt, loop_scope):
        cond_expr = self.rewrite_expr(stmt.test, loop_scope)
        pre_branch_index = self.variable_index.copy()

        branch_if_constraints, index_after_if = self.execute_branch(stmt.body, loop_scope, pre_branch_index)
        branch_else_constraints, index_after_else = self.execute_branch(stmt.orelse or [], loop_scope, pre_branch_index)

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

        self.constraints.extend([
            Constraint(c.expression, c.conditions + [cond_expr]) for c in branch_if_constraints
        ])
        self.constraints.extend([
            Constraint(c.expression, c.conditions + [f"(not {cond_expr})"]) for c in branch_else_constraints
        ])

    def execute_block_assert(self, stmt, loop_scope):
        test_expr = self.rewrite_expr(stmt.test, loop_scope)
        self.constraints.append(Constraint(test_expr))

    def execute_block(self, block, loop_scope):
        for stmt in block:
            if isinstance(stmt, ast.Assign):
                self.execute_block_assign(stmt, loop_scope)
            elif isinstance(stmt, ast.For):
                self.execute_block_for(stmt, loop_scope)
            elif isinstance(stmt, ast.If):
                self.execute_block_if(stmt, loop_scope)
            elif isinstance(stmt, ast.Assert):
                self.execute_block_assert(stmt, loop_scope)
            else:
                raise ValueError(f"Unsupported statement: {ast.dump(stmt, include_attributes=False)}")


class Predicate(CodeBlock):
    def __init__(self,
                 code,
                 n_inputs=0,
                 n_outputs=0,
                 function_name=""):
        super().__init__(code)
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.function_name = function_name
        self.execute_block(ast.parse(code).body, {})
        self.constraints = [str(c) for c in self.constraints if c is not None]

    def predicate_definition(self):
        pred_def = f"predicate {self.function_name}("
        if self.n_inputs > 0:
            pred_def += ", ".join([f"int: input_{i+1}" for i in range(self.n_inputs)])
        if self.n_outputs > 0:
            pred_def += ", ".join([f"var int: output_{i+1}" for i in range(self.n_outputs)])
        if len(self.variable_declarations) > 0:
            pred_def += ", ".join(self.variable_declarations)
        pred_def += ")"
        conditions = ' /\\ '.join(self.constraints)
        return f"{pred_def} =\n    (\n    {conditions}\n    );"

    def predicate_call(self, inputs, outputs, n_call=1):
        if len(inputs) != self.n_inputs:
            raise ValueError(f"Expected {self.n_inputs} inputs, got {len(inputs)}")
        if len(outputs) != self.n_outputs:
            raise ValueError(f"Expected {self.n_outputs} outputs, got {len(outputs)}")
        call_args = [f"{inputs[i]}" for i in range(self.n_inputs)]
        call_args += [f"{outputs[i]}" for i in range(self.n_outputs)]
        call_args += [f"{var}{n_call}" for var in self.variable_declarations]



if __name__ == "__main__":
    # Test the MiniZinc translation with the provided code
    translator = MiniZincTranslator(code_check_machine)
    print(translator.unroll_translation())
