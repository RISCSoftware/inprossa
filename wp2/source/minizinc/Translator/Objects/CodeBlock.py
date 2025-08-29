import ast
from collections import defaultdict
from Translator.Objects.Constraint import Constraint
from Translator.Objects.Declaration import Declaration


class CodeBlock:
    """
    Executes a block of Python statements, tracks:
      - symbol_table (UPPERCASE constants)
      - is_constant (set of constant names)
      - variable_index (versioning x[1], x[2], ...)
      - variable_declarations (var type/domain)
      - constraints (generated Constraint objects)
      - extra_array_decls (arrays needed for predicate calls, e.g., a1,b1,c1,d1)
      - predicate_call_counts (for unique array suffixes per predicate)

    Provides helpers to emit MiniZinc declarations and constraints for this block.
    """

    def __init__(self, *, symbol_table=None, predicates=None):
        # Tracks the current version (index) of each variable (e.g., x[0], x[1], ...)
        self.variable_index = {}
        # varname → (type, domain), e.g. ('int', [4,10]), ('float', [4.0,10.0])
        self.evolving_vars_declrs = {}
        # varname → Declaration
        self.all_variable_declarations = {}
        # Tracks the set of constant (symbolic) names, identified by being all uppercase
        self.symbol_table = {} if symbol_table is None else dict(symbol_table)
        self.is_constant = set(self.symbol_table.keys())
        # List of accumulated constraints generated during symbolic execution
        self.constraints = []
        # Predicate registry: name -> Predicate
        self.predicates = {} if predicates is None else dict(predicates)
        # Counter per predicate for unique call arrays (a1,b1,...) then (a2,b2,...)
        self.predicate_call_counts = defaultdict(int)

    def run(self, block, loop_scope=None):
        """Execute an AST statement list (block)."""
        self.execute_block(block, {} if loop_scope is None else loop_scope)
        # Add declarations of the evolving variables now that we know their length
        self.evolving_vars_declaration()
        return self

    def get_symbol_declarations(self):
        """Declare constants as MiniZinc symbols (not evolving)."""
        decls = []
        for name, val in self.symbol_table.items():
            if isinstance(val, int):
                decls.append(f"int: {name} = {val};")
            elif isinstance(val, list):
                decls.append(f"array[1..{len(val)}] of int: {name} = [{', '.join(map(str, val))}];")
        return decls
    
    def get_all_vars_declrs(self):
        """Get all variable declarations (evolving and non-evolving)."""
        return [declr.to_minizinc() for declr in self.all_variable_declarations.values()]

    def evolving_vars_declaration(self):
        """Declare arrays for evolving variables in this block."""
        decls = []
        for var, size in self.variable_index.items():
            if var not in self.evolving_vars_declrs:
                print(f"Variable '{var}' used but not declared: assuming type 'int'")
            var_declr = self.evolving_vars_declrs.get(var, Declaration(var, type_="int"))
            # default int if explicitly assigned
            var_declr.define_size(size)
            self.all_variable_declarations[var] = var_declr
        return decls

    # TODO Merge the declarations and run the get?... in minizinc translator

    def get_constraints(self):
        return [str(c) for c in self.constraints if c is not None]

    def new_evolving_variable(self, name, type_=None, lower=None, upper=None):
        """New variable is detected, we add it to the variable index and create its declaration."""
        if type_ is None:
            print(f"Warning: Variable '{name}' used without assignment: assuming type 'int'")
            type_ = "int"
        self.variable_index[name] = 1
        if name not in self.evolving_vars_declrs:
            self.evolving_vars_declrs[name] = Declaration(name, type_=type_)

    def rewrite_expr(self, expr, loop_scope):
        """
        Converts a Python expression AST into a MiniZinc-compatible string
        """
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
                self.new_evolving_variable(name)

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

            # Only support known functions like abs, max, min (not user-defined here)
            if func_name in {"abs", "max", "min"}:
                args = [self.rewrite_expr(arg, loop_scope) for arg in expr.args]
                return f"{func_name}({', '.join(args)})"
            else:
                raise ValueError(f"Unsupported function call in expression: {func_name}")

        else:
            # Fallback: use source-like syntax
            return ast.unparse(expr)

    # --- Execute blocks (assignments, for, if, functions, type declarations, asserts...) ---

    def execute_block(self, block, loop_scope):
        """Recursively execute a block of Python statements, updating symbolic state"""
        for stmt in block:
            # Handle assignment statements
            if isinstance(stmt, ast.Assign):
                self.execute_block_assign(stmt, loop_scope)

            elif isinstance(stmt, ast.For):
                self.execute_block_for(stmt, loop_scope)

            elif isinstance(stmt, ast.If):
                self.execute_block_if(stmt, loop_scope)

            elif isinstance(stmt, ast.Assert):
                self.execute_block_assert(stmt, loop_scope)

            elif isinstance(stmt, ast.AnnAssign):
                self.execute_block_annassign(stmt, loop_scope)

            elif isinstance(stmt, ast.FunctionDef):
                # ignore: functions handled by MiniZincTranslator/Predicate
                continue
            else:
                print(type(stmt))
                raise ValueError(f"Unsupported statement: {ast.dump(stmt, include_attributes=False)}")

    # --- ASSIGNMENTS ---

    def execute_block_assign(self, stmt, loop_scope):
        """
        Handle tuple assignment from predicate call: e.g., c, d = f(a, b)
        """
        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
            fname = stmt.value.func.id
            if fname in self.predicates:
                return self._handle_predicate_call_assign(stmt, loop_scope, self.predicates[fname])

        # Normal assignment
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
        if var not in self.variable_index:
            self.new_evolving_variable(var)
        else:
            self.variable_index[var] += 1
        self.constraints.append(Constraint(f"{var}[{self.variable_index[var]}] = {rhs}"))

    def _handle_predicate_call_assign(self, stmt, loop_scope, pred):
        """Handle assignments like: e, g = f(c, d)."""
        # Outputs on LHS
        if isinstance(stmt.targets[0], ast.Tuple):
            out_exprs = [self.rewrite_expr(elt, loop_scope) for elt in stmt.targets[0].elts]
        else:
            out_exprs = [self.rewrite_expr(stmt.targets[0], loop_scope)]

        if len(out_exprs) != pred.n_outputs:
            raise ValueError(f"Predicate '{pred.name}': expected {pred.n_outputs} outputs, got {len(out_exprs)}")

        # Inputs on RHS call
        call = stmt.value
        in_exprs = [self.rewrite_expr(arg, loop_scope) for arg in call.args]
        if len(in_exprs) != pred.n_inputs:
            raise ValueError(f"Predicate '{pred.name}': expected {pred.n_inputs} inputs, got {len(in_exprs)}")

        # Unique arrays for this call (a1,b1,c1,d1), (a2,b2,c2,d2), ...
        self.predicate_call_counts[pred.name] += 1
        call_idx = self.predicate_call_counts[pred.name]

        array_arg_names = []
        # Use the same order as predicate arrays_order
        for v in pred.arrays_order:
            size = pred.local_array_sizes[v]
            arr_name = f"{v}__{call_idx}"
            array_arg_names.append(arr_name)
            # Declare arrays needed for this call
            self.all_variable_declarations[arr_name] = Declaration(arr_name, dims=size, type_="int")

        # Emit the predicate call as a constraint
        call_line = pred.emit_call_line(in_exprs, out_exprs, array_arg_names)
        self.constraints.append(Constraint(call_line))

    # --- FOR LOOPS---

    def execute_block_for(self, stmt, loop_scope):
        iter_values = []
        loop_vars = []
        meta = {}

        # Handle for-loops, including range and enumerate
        if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
            func_id = stmt.iter.func.id

            if func_id == "range":
                # range(start, end)
                iter_values, loop_vars = self._resolve_range_iter(stmt)
                meta.update(kind="range", array_name=None)

            # enumerate([...]) or enumerate(PIECES)
            # e.g. PIECES = [2, 5, 3]
            # for current_index, piece in enumerate(PIECES):
            elif func_id == "enumerate":
                iter_values, loop_vars = self._resolve_enumerate_iter(stmt)

            else:
                raise ValueError(f"Unsupported function call iterator: {ast.unparse(stmt.iter)}")

        # Case 2: iterate over list literal: for x in [1, 2, 3]
        elif isinstance(stmt.iter, ast.List):
            iter_values = [elt.value for elt in stmt.iter.elts]
            loop_vars = [stmt.target.id]
            meta.update(kind="list", array_name=None)

        # Case 3: iterate over constant name: for x in PIECES
        elif isinstance(stmt.iter, ast.Name):
            const_name = stmt.iter.id
            if const_name in self.symbol_table:
                # iterate by 1-based index to keep symbolic access
                n = len(self.symbol_table[const_name])
                iter_values = list(range(1, n + 1))  # positions
                loop_vars = [stmt.target.id]
                meta.update(kind="const", array_name=const_name)
            else:
                raise ValueError(f"Unknown constant array: {const_name}")

        # Anything else is unsupported
        else:
            raise ValueError(f"Unsupported loop iterator: {ast.unparse(stmt.iter)}")

        # Iterate through values and execute body with updated loop variable bindings
        for k, item in enumerate(iter_values, start=1):
            new_scope = self._bind_loop_variables(stmt, loop_scope, loop_vars, meta, k, item)
            self.execute_block(stmt.body, new_scope)

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

    def _bind_loop_variables(self, stmt, loop_scope, loop_vars, meta, k, item):
        """
        Bind loop variables for this iteration.
        k is 1-based iteration counter for const arrays.
        item is the current element (or (index, value) for enumerate).
        """
        new_scope = loop_scope.copy()

        # enumerate(...)
        if hasattr(stmt.iter, "func") and isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "enumerate":
            index_var, element_var = loop_vars
            index_val, element_val = item
            new_scope[index_var] = index_val

            # Is it enumerate(NAME) or enumerate([ ... ]) ?
            arg0 = stmt.iter.args[0]
            array_name = arg0.id if isinstance(arg0, ast.Name) else None

            if array_name:
                # enumerate(CONST_ARRAY) → symbolic access CONST[index]
                new_scope[element_var] = f"{array_name}[{index_val}]"
            else:
                # enumerate([v1,v2,...]) → bind literal value
                new_scope[element_var] = element_val

            return new_scope

        # for t in CONST_ARRAY
        if meta.get("kind") == "const":
            (loop_var,) = loop_vars
            array_name = meta["array_name"]
            new_scope[loop_var] = f"{array_name}[{k}]"
            return new_scope

        # for t in [list literal]
        if meta.get("kind") == "list":
            (loop_var,) = loop_vars
            new_scope[loop_var] = item
            return new_scope

        # for i in range(a,b)
        if meta.get("kind") == "range":
            (loop_var,) = loop_vars
            new_scope[loop_var] = item
            return new_scope

        # default (should not happen)
        raise Exception("Kind of loop unknown")
    
    # --- IF ---

    def merge_variable(self, var, idx_if, idx_else):
        """
        Merges variable versions after an if-else branch by using the highest index
        """
        merged_idx = max(idx_if, idx_else)
        self.variable_index[var] = merged_idx
        constraints = dict()

        if idx_if != merged_idx:
            if idx_if == 0:
                # If the variable was not assigned in the if-branch,
                # we can use a special UNDEFINED value (skipped here)
                # TODO think about whether this is the behavior we want
                print(f"Warning: Variable '{var}' not assigned in if-branch")
            else:
                constraints["if"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_if}]")

        if idx_else != merged_idx:
            if idx_else == 0:
                print(f"Warning: Variable '{var}' not assigned in else-branch")
            else:
                constraints["else"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_else}]")

        return constraints

    def execute_branch(self, block, loop_scope, pre_index):
        """
        Executes a code block (body of if or else) independently and returns resulting state
        """
        constraints_backup = self.constraints.copy()
        self.constraints.clear()
        self.variable_index = pre_index.copy()
        self.execute_block(block, loop_scope)
        result_constraints = self.constraints[:]
        result_index = self.variable_index.copy()
        self.constraints = constraints_backup
        return result_constraints, result_index

    def execute_block_if(self, stmt, loop_scope):
        # Handle if-statements with symbolic branching
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

    # --- ASSERTIONS ---

    def execute_block_assert(self, stmt, loop_scope):
        # Handle assert statements
        test_expr = self.rewrite_expr(stmt.test, loop_scope)
        self.constraints.append(Constraint(test_expr))

    # --- TYPE DECLARATIONS ---

    def execute_block_annassign(self, stmt, loop_scope):
        self.evolving_vars_declrs[stmt.target.id] = Declaration(stmt.target.id, type_=stmt.annotation.id)
        if stmt.value is not None:
            self.new_evolving_variable(stmt.target.id, loop_scope)
            self.variable_index[stmt.target.id] += 1
            self.constraints.append(Constraint(f"{stmt.target.id}[{self.variable_index[stmt.target.id]}] = {stmt.value.value}"))
