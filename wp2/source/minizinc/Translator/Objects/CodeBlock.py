import ast
from collections import defaultdict
from Translator.Objects.Constraint import Constraint
from Translator.Objects.DSTypes import DSInt, DSList, compute_type
from Translator.Objects.Variable import Variable
from itertools import product
from Translator.Objects.Constant import Constant, ast_to_object
from Translator.Tools import ExpressionRewriter
import copy
class CodeBlock:
    """
    Executes a block of Python statements, tracks:
      - constant_table (UPPERCASE constants)
      - variable_index (versioning x[1], x[2], ...)
      - variable_declarations (var type/domain)
      - constraints (generated Constraint objects)
      - extra_array_decls (arrays needed for predicate calls, e.g., a1,b1,c1,d1)

    Provides helpers to emit MiniZinc declarations and constraints for this block.
    """

    def __init__(self, *, constant_table=None, predicates=None, types=None):
        # varname → Variable
        self.variable_table = {}
        # Tracks the set of constant (symbolic) names, identified by being all uppercase
        self.constant_table = {} if constant_table is None else dict(constant_table)
        # List of accumulated constraints generated during symbolic execution
        self.constraints = []
        # Predicate registry: name -> Predicate
        self.predicates = {} if predicates is None else dict(predicates)
        # Type registry: name -> DSType
        self.types = {} if types is None else dict(types)

    def run(self, block, loop_scope=None):
        """Execute an AST statement list (block)."""
        

        # Define the objective function
        self.new_evolving_variable("objective", DSInt())
        # and initialize to 0
        self.create_deep_equality_constraint(self.variable_table["objective"], [], "0")
        
        self.execute_block(block, {} if loop_scope is None else loop_scope)
        # Add declarations of the evolving variables now that we know their length
        return self
    # TODO Merge the declarations and run the get?... in minizinc translator

    def new_evolving_variable(self, name, type_=None, versions=1):
        """New variable is detected, we add it to the variable index and create its declaration."""
        self.variable_table[name] = Variable(name, type_=type_, versions=versions, known_types=self.types, constant_table=self.constant_table)

    # --- Execute blocks (assignments, for, if, functions, type declarations, asserts...) ---

    def execute_block(self, block, loop_scope):
        """Recursively execute a block of Python statements, updating symbolic state"""
        for stmt in block:
            # Handle assignment statements
            if isinstance(stmt, ast.Assign):
                self.execute_block_assign(stmt.targets[0], stmt.value, loop_scope)

            elif isinstance(stmt, ast.For):
                self.execute_block_for(stmt, loop_scope)

            elif isinstance(stmt, ast.If):
                self.execute_block_if(stmt, loop_scope)

            elif isinstance(stmt, ast.Assert):
                print("Executing assert on:", ast.dump(stmt, include_attributes=False))
                self.execute_block_assert(stmt, loop_scope)

            elif isinstance(stmt, ast.AnnAssign):
                self.execute_block_annassign(stmt, loop_scope)

            elif isinstance(stmt, ast.FunctionDef):
                # ignore: functions handled by MiniZincTranslator/Predicate
                continue
            elif isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Name):
                fname = stmt.func.id
                if fname in self.predicates:
                    return self._handle_predicate_call_assign(None, stmt, loop_scope, self.predicates[fname])
                else:
                    raise ValueError(f"Unknown predicate/function called: {fname}")
            elif isinstance(stmt, ast.Expr):
                self.execute_block([stmt.value], loop_scope)
            else:
                raise ValueError(f"Unsupported statement: {ast.dump(stmt, include_attributes=False)}")

    # --- ASSIGNMENTS ---

    def execute_block_assign(self, lhs, rhs, loop_scope):
        """
        Handle assignment statements, including:
            - predicate call assignments: c, d = f(a, b)
            - simple assignments: x = expr
            - subscript assignments: a[i] = expr
            - constant definitions: MAX_LENGTH = 10
            - array assignments: A = [1,2,3]
        """
        # TODO receive left-hand side and right hand side separately
        # First check if its a function, then check if lhs is a tuple (if so, multiple assignments)


        # Assignment from a predicate call: e.g., c, d = f(a, b)
        # These are handled separetely because it's translated to a predicate call
        if isinstance(rhs, ast.Call) and isinstance(rhs.func, ast.Name):
            fname = rhs.func.id
            if fname in self.predicates:
                return self._handle_predicate_call_assign(lhs, rhs, loop_scope, self.predicates[fname])
            else:
                if fname[:2] != "DS":
                    raise ValueError(f"Unknown predicate/function called: {fname}")

        # Rewrite right-hand side expression
        rhs_expr = ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(rhs)

            
        # Subscript assignment: e.g., a[1] = 5
        if isinstance(lhs, ast.Subscript):
            self.find_original_variable_and_assign(lhs, rhs_expr, rhs, loop_scope)
            return

        # TODO Dictionary assignment: e.g., rec["field"] = value

        # Object attribute assignment: e.g., obj.attr = value
        if isinstance(lhs, ast.Attribute):
            self.find_original_variable_and_assign(lhs, rhs_expr, rhs, loop_scope)
            return

        # Normal assignment # TODO Maybe the previous cases can be deleted
        var = lhs.id

        # Detect and record constant definitions (uppercase names)
        if var.isupper():
            # TODO allow if the constant is an int
            raise Exception("Constant definitions should indicate their type:", var)

        # For evolving variables, emit a versioned constraint
        if var not in self.variable_table:
            self.new_evolving_variable(var)

        
        self.find_original_variable_and_assign(lhs, rhs_expr, rhs, loop_scope)
        # type_ = self.create_equality_constraint(self.variable_table[var].versioned_name(), rhs_expr, rhs, loop_scope)
        # if self.variable_table[var].type == None:
        #     self.variable_table[var].define_type(type_)

    def find_original_variable_and_assign(self, lhs, rhs_expr=None, rhs=None, loop_scope=None):
        """Finds the original variable name from a potentially nested attribute/subscript access."""
        obj_name = " "
        my_lhs = lhs
        assigned_chain = [] # to store the attribute/subscript chain
        if isinstance(my_lhs, ast.Name):
            original_name = my_lhs.id
        else:
            original_name = None
        i = 0
        while obj_name not in self.variable_table and obj_name not in self.constant_table:
            old_obj_name = obj_name
            if isinstance(my_lhs, ast.Attribute):
                assigned_chain.insert(0, ("dict", ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(my_lhs.attr)))
                my_lhs = my_lhs.value
            elif isinstance(my_lhs, ast.Subscript):
                assigned_chain.insert(0, ("list", ExpressionRewriter(loop_scope, code_block=self).get_expr_value(my_lhs.slice)))
                my_lhs = my_lhs.value
            
            if hasattr(my_lhs, "id"):
                obj_name = my_lhs.id
                if obj_name == old_obj_name:
                    if obj_name == original_name:
                        # If its an unseen variable without attributes/subscripts, create it assuming int
                        self.new_evolving_variable(obj_name)
                    else:
                        raise ValueError(f"Variable '{obj_name}' not defined in variable table.")
            i += 1
            if i > 20:
                raise ValueError("Too many iterations finding original variable.")

        if obj_name in self.variable_table:
            var_obj = self.variable_table[obj_name]
            self.create_deep_equality_constraint(var_obj, assigned_chain, rhs_expr, rhs, loop_scope)
        elif obj_name in self.constant_table:
            const_obj = self.constant_table[obj_name]
            const_obj.assign_chain(const_obj.value_structure, assigned_chain, rhs)

    def create_deep_equality_constraint(self, var_obj, chain, rhs_expr=None, rhs=None, loop_scope=None):
        """Creates equality constraints for nested attribute/subscript assignments."""
        is_unassigned = var_obj.is_chain_unassigned(chain)
        # Learn whether the field is already assigned
        if not is_unassigned:
            # If assigned, create a new version for the base variable
            # all the already assign fields must preserve the value in the new version
            self.new_var_version_and_preserve_assigned(var_obj, chain)
        # In any case, create the equality constraint for the field being assigned and mark it as assigned
        lhs_name = var_obj.versioned_name() + self.chain_to_appended_text(chain)
        var_obj.assigned_fields = var_obj.mark_chain_as_assigned(chain)
        if rhs_expr is not None:
            fields_after_chain = var_obj.fields_after_chain(chain)
            self.create_equality_constraint(lhs_name, rhs_expr, rhs, loop_scope, fields=fields_after_chain)

    def new_var_version_and_preserve_assigned(self, var_obj, chain):
        """Creates a new version of var_obj, preserving assigned fields."""
        old_version_name = var_obj.versioned_name()
        var_obj.versions += 1
        new_version_name = var_obj.versioned_name()
        assigned_chains = var_obj.collect_assigned_chains(var_obj.assigned_fields)
        for new_chain in assigned_chains:
            if len(new_chain) < len(chain) or new_chain[:len(chain)] != chain:
                # Make sure this new chain is not under the chain being assigned
                full_chain = new_chain
                # Create equality constraint for this chain
                appended_text_for_chain = self.chain_to_appended_text(full_chain)
                self.constraints.append(Constraint(f"{new_version_name}{appended_text_for_chain} = {old_version_name}{appended_text_for_chain}"))

    def chain_to_appended_text(self, chain):
        """Converts an access chain to MiniZinc syntax."""
        appended_text = ""
        for step_type, step in chain:
            if step_type == "list":
                appended_text += f"[{step}]"
            elif step_type == "dict":
                appended_text += f".{step}"
            else:
                raise TypeError(f"Invalid access step: {step}")
        return appended_text

    def create_equality_constraint(self, lhs_name, rhs_expr, rhs, loop_scope, fields=None):
        if fields is not None and fields != 0:
            # Iterate through the content of the type to create the constraints
            # 0 means that we are at the final field
            if isinstance(fields, dict):
                for key, subfields in fields.items():
                    new_lhs_name = f"{lhs_name}.{key}"
                    self.create_equality_constraint(new_lhs_name, rhs_expr + f".{key}", rhs, loop_scope, fields=subfields)
            elif isinstance(fields, list):
                for index, subfields in enumerate(fields):
                    new_lhs_name = f"{lhs_name}[{index + 1}]"
                    self.create_equality_constraint(new_lhs_name, rhs_expr + f"[{index + 1}]", rhs, loop_scope, fields=subfields)

        # elif isinstance(rhs, ast.List):
        #     length = len(rhs.elts)
        #     list_elem_type = []
        #     for index in range(1, length + 1):
        #         elem_type = self.create_equality_constraint(f"{lhs_name}[{index}]", f"{rhs_expr}[{index}]", rhs.elts[index - 1], loop_scope)
        #         list_elem_type.append(elem_type.representation() if not isinstance(elem_type, str) else elem_type) # Make sure they are of the same type
        #     if len(set(list_elem_type)) != 1:
        #         raise ValueError(f"List elements have inconsistent types: {list_elem_type}")
        #     return DSList(length, elem_type=elem_type)
        else:
            self.constraints.append(Constraint(f"{lhs_name} = {rhs_expr}"))
            return "int" # TODO infer type from rhs


    def record_constant_definition(self, value_node):
        """Extracts the value of a constant definition from its AST node."""
        if isinstance(value_node, ast.List):
            return [self.record_constant_definition(elt) for elt in value_node.elts]
        else:
            return self.rewrite_expr(value_node, {})
            raise ValueError(f"Unsupported constant definition: {ast.dump(value_node, include_attributes=False)}")

    def _handle_predicate_call_assign(self, lhs, rhs, loop_scope, pred):
        """Handle assignments like: e, g = f(c, d)."""

        # Outputs on LHS
        out_exprs = []
        if lhs is None:
            # No outputs
            out_exprs = []
        elif isinstance(lhs, ast.Tuple):
            # Multiple outputs
            for elt in lhs.elts:
                # Taking into account the output vars actualise version and assigned fields accordingly
                self.find_original_variable_and_assign(elt)
                # Write the output expression with appropriate versions
                out_exprs.append(ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(elt))
        else:
            # Single output
            # Taking into account the output var actualise version and assigned fields accordingly
            self.find_original_variable_and_assign(lhs)
                # Write the output expression with appropriate versions
            out_exprs.append(ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(lhs))

        if len(out_exprs) != pred.n_outputs:
            raise ValueError(f"Predicate '{pred.name}': expected {pred.n_outputs} outputs, got {len(out_exprs)}")

        # Inputs on RHS call
        in_exprs = [ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(arg) for arg in rhs.args]
        if len(in_exprs) != pred.n_inputs:
            raise ValueError(f"Predicate '{pred.name}': expected {pred.n_inputs} inputs, got {len(in_exprs)}")

        # Unique arrays for this call (a__1,b__1,c__1,d__1), (a__2,b__2,c__2,d__2), ...
        pred.call_count += 1
        call_idx = pred.call_count


        array_arg_names = []
        # Use the same order as predicate arrays_order
        for v in pred.arrays_order:
            var_obj = pred.variable_table[v]
            arr_name = f"{v}__{pred.name}__{call_idx}"
            array_arg_names.append(arr_name)
            # Declare arrays needed for this call
            self.variable_table[arr_name] = Variable(arr_name,
                                                     versions=var_obj.versions,
                                                     type_=var_obj.type)

        # Emit the predicate call as a constraint
        call_line = pred.emit_call_line(in_exprs, out_exprs, array_arg_names)
        self.constraints.append(Constraint(call_line))
        # Add the objective function constraint
        obj_in_func_name = f"objective__{pred.name}__{call_idx}"
        # Desired constraint in text
        desired_constraint_text = f"objective = objective + {obj_in_func_name}"
        # Turn it into ast
        desired_constraint_ast = ast.parse(desired_constraint_text, mode='exec')
        # Introduce desired constraint by executing block
        self.execute_block(desired_constraint_ast.body, loop_scope={})

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
                iter_values, loop_vars = self._resolve_range_iter(stmt, loop_scope)
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
            if const_name in self.constant_table:
                # iterate by 1-based index to keep symbolic access
                const_type = self.constant_table[const_name].type
                if isinstance(const_type, DSList):
                    n = const_type.length
                elif isinstance(const_type, str):
                    n = self.types[const_type].length
                else:
                    raise ValueError(f"Unsupported constant type for array iteration: {const_type}")
                iter_values = list(range(1, n + 1))  # positions
                loop_vars = [stmt.target.id]
                meta.update(kind="const", array_name=const_name)
            elif const_name in self.variable_table:
                var_obj = self.variable_table[const_name]
                var_type = var_obj.type
                if isinstance(var_type, DSList):
                    n = var_type.length
                else:
                    raise ValueError(f"Unsupported variable type for array iteration: {var_type}")
                iter_values = list(range(1, n + 1))  # positions
                loop_vars = [stmt.target.id]
                versioned_const_name = var_obj.versioned_name()
                meta.update(kind="const", array_name=versioned_const_name)

            else:
                raise ValueError(f"Unknown constant array: {const_name}")

        # Anything else is unsupported
        else:
            raise ValueError(f"Unsupported loop iterator: {ast.unparse(stmt.iter)}")

        # Iterate through values and execute body with updated loop variable bindings
        for k, item in enumerate(iter_values, start=1):
            new_scope = self._bind_loop_variables(stmt, loop_scope, loop_vars, meta, k, item)
            self.execute_block(stmt.body, new_scope)

    def _resolve_range_iter(self, stmt, loop_scope):
        
        if len(stmt.iter.args) == 1:
            # range(end) → start=1, end=arg0
            start_node = ast.Constant(value=1)
            end_node = stmt.iter.args[0]
        else:
            # range(start, end)
            start_node = stmt.iter.args[0]
            end_node = stmt.iter.args[1]

        # Evaluate start
        start_val = ExpressionRewriter(loop_scope, code_block=self).get_expr_value(start_node)
        # if isinstance(start_node, ast.Constant):
        #     start_val = start_node.value
        # elif isinstance(start_node, ast.Name) and start_node.id in self.constant_table:
        #     start_val = int(self.constant_table[start_node.id].value_structure) # TODO generalise other ways of accessing constants and their parts
        # else:
        #     raise ValueError(f"Unsupported start in range: {ast.unparse(start_node)}")

        # Evaluate end
        end_val = ExpressionRewriter(loop_scope, code_block=self).get_expr_value(end_node)
        # if isinstance(end_node, ast.Constant):
        #     end_val = end_node.value
        # elif isinstance(end_node, ast.Name) and end_node.id in self.constant_table:
        #     end_val = int(self.constant_table[end_node.id].value_structure)

        # else:
        #     raise ValueError(f"Unsupported end in range: {ast.unparse(end_node)}")

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
            iter_values = list(enumerate(values, start=1))
            # iter_values: [(1, 2), (2, 5), (3, 3)]
            loop_vars = [elt.id for elt in stmt.target.elts]
            # loop_vars: ['current_index', 'piece']
        # enumerate over constant array like PIECES
        elif isinstance(arg, ast.Name) and arg.id in self.constant_table:
            values = self.constant_table[arg.id]
            iter_values = list(enumerate(values, start=1))
            # iter_values: [(1, 2), (2, 5), (3, 3)]
            loop_vars = [elt.id for elt in stmt.target.elts]
            # loop_vars: ['current_index', 'piece']
        elif isinstance(arg, ast.Name) and arg.id in self.variable_table:
            var_obj = self.variable_table[arg.id]
            var_type = var_obj.type
            if isinstance(var_type, DSList):
                n = var_type.length
            else:
                raise ValueError(f"Unsupported variable type for array iteration: {var_type}")
            versioned_const_name = var_obj.versioned_name()
            iter_values = [(i, f"{versioned_const_name}[{i}]") for i in range(1, n + 1)]  # positions
            loop_vars = [elt.id for elt in stmt.target.elts]
            # Edit the second loop var to be the array access
        else:
            raise ValueError(f"Unsupported enumerate argument: {ast.unparse(arg)}")
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
        if var not in self.variable_table:
            self.new_evolving_variable(var)
        self.variable_table[var].versions = merged_idx
        constraints = dict()

        if idx_if != merged_idx:
            if idx_if == 0:
                # If the variable was not assigned in the if-branch,
                # we can use a special UNDEFINED value (skipped here)
                # TODO think about whether this is the behavior we want
                # print(f"Warning: Variable '{var}' not assigned in if-branch")
                pass
            else:
                constraints["if"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_if}]")

        if idx_else != merged_idx:
            if idx_else == 0:
                # print(f"Warning: Variable '{var}' not assigned in else-branch")
                pass
            else:
                constraints["else"] = Constraint(f"{var}[{merged_idx}] = {var}[{idx_else}]")

        return constraints

    def execute_branch(self, block, loop_scope, pre_table):
        """
        Executes a code block (body of if or else) independently and returns resulting state
        """
        constraints_backup = copy.deepcopy(self.constraints)
        self.constraints.clear()
        self.variable_table = copy.deepcopy(pre_table)
        self.execute_block(block, loop_scope)
        result_constraints = self.constraints[:]
        result_index = copy.deepcopy(self.variable_table)
        self.constraints = constraints_backup
        return result_constraints, result_index

    def execute_block_if(self, stmt, loop_scope):
        # Handle if-statements with symbolic branching
        cond_expr = ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(stmt.test)
        pre_branch_index = copy.deepcopy(self.variable_table)

        # Run both if and else branches independently
        branch_if_constraints, index_after_if = self.execute_branch(stmt.body, loop_scope, pre_branch_index)
        branch_else_constraints, index_after_else = self.execute_branch(stmt.orelse or [], loop_scope, pre_branch_index)

        # Merge variable versions from both branches
        all_vars = set(index_after_if) | set(index_after_else)
        for var in all_vars:
            idx_before = pre_branch_index.get(var, Variable(name="", versions=0))
            idx_if = index_after_if.get(var, idx_before).versions
            idx_else = index_after_else.get(var, idx_before).versions
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
        test_expr = ExpressionRewriter(loop_scope, code_block=self).rewrite_expr(stmt.test)
        self.constraints.append(Constraint(test_expr))

    # --- TYPE DECLARATIONS ---

    def execute_block_annassign(self, stmt, loop_scope):
        type_ = compute_type(stmt.annotation, known_types=self.types, constant_table=self.constant_table)
        var = stmt.target.id
        if var.isupper():
            # Save in constants; name, value and type
            # constant_value = self.record_constant_definition(stmt.value)
            self.constant_table[var] = Constant(var, stmt_value=stmt.value, type_=type_, code_block=self, loop_scope=loop_scope)
            return  # Don't emit constraint for constants
        
        else:
            if var not in self.variable_table:
                self.new_evolving_variable(var, type_=type_)
            # TODO call execute_block_assign to handle assignment
            if stmt.value is not None:
                self.execute_block_assign(stmt.target, stmt.value, loop_scope)
            # value = self.rewrite_expr(stmt.value, loop_scope) if stmt.value is not None else None
            # if value is not None:
            #     self.create_deep_equality_constraint(self.variable_table[var], [], value, stmt.value, loop_scope)
            #     # self.create_equality_constraint(self.variable_table[var].versioned_name(), value, stmt.value, loop_scope, fields=type_.initial_assigned_fields())


def all_indices(shape):
    """Yield 1-based index tuples for an n-D array of given sizes."""
    # e.g. shape=[2,4] -> (1..2)×(1..4)
    for idx in product(*(range(1, n+1) for n in shape)):
        yield idx
