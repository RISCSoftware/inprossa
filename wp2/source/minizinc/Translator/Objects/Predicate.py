import ast
from Translator.Objects.CodeBlock import CodeBlock

    
class Predicate(CodeBlock):
    """Translate a Python function into a MiniZinc predicate."""
    def __init__(self, func_node: ast.FunctionDef, predicates=None, types=None, constant_table=None, name_override: str | None = None):
        super().__init__(constant_table=constant_table, predicates=predicates, types=types)
        self.func_node = func_node
        self.name = name_override if name_override is not None else func_node.name
        # Printing the tree of the function for debugging
        self.input_names = [a.arg for a in func_node.args.args]
        self.input_types = [a.annotation for a in func_node.args.args]
        # TODO collect the types of the inputs from annotations
        self.n_inputs = len(self.input_names)
        self.return_names = self._extract_return_names(func_node)
        self.n_outputs = len(self.return_names)
        # Counter per predicate for unique call arrays (a1,b1,...) then (a2,b2,...)
        self.call_count = 0

        # Ensure inputs have at least one version and will be tied to input_i
        print("Predicate input names:", self.input_names)
        for i_name, i_type in zip(self.input_names, self.input_types):
            print("Input name:", i_name)
            if i_name not in self.variable_table:
                self.new_evolving_variable(i_name, type_=i_type)

        # Execute function body to collect constraints and versioning
        func_body = [s for s in func_node.body if not isinstance(s, ast.Return)]
        self.run(func_body, loop_scope={})

        # Internal arrays order and sizes (stable ordering)

        self.arrays_order = sorted(self.variable_table.keys())

    def _extract_return_names(self, func_node):
        # Find first/last return in function (use last)
        returns = [n for n in func_node.body if isinstance(n, ast.Return)]
        if not returns:
            return []
        ret = returns[-1]
        if isinstance(ret.value, ast.Tuple):
            names = []
            for elt in ret.value.elts:
                if isinstance(elt, ast.Name):
                    names.append(elt.id)
                else:
                    raise ValueError("Only simple names supported in return tuple.")
            return names
        elif isinstance(ret.value, ast.Name):
            return [ret.value.id]
        else:
            raise ValueError("Only returning names or tuple of names is supported.")

    def emit_definition(self):
        """Return the MiniZinc predicate definition string."""
        # Parameters: inputs, outputs, then arrays in variable declarations
        params = []
        # inputs
        params += [f"var int: input_{i+1}" for i in range(self.n_inputs)]
        # outputs
        params += [f"var int: output_{i+1}" for i in range(self.n_outputs)]
        # arrays (as var int arrays)
        for v in self.arrays_order:
            params += [self.variable_table[v].to_minizinc()]

        # Build boolean body: input inits, function constraints, output bindings
        exprs = []

        # a[1] = input_1, b[1] = input_2, ...
        for i, in_name in enumerate(self.input_names, start=1):
            exprs.append(f"{in_name}[1] = input_{i}")

        # constraints from function body (convert to bool exprs)
        for c in self.constraints:
            exprs.append(c.as_bool_expr())

        # output_k = last_version(return_name)
        for k, ret_name in enumerate(self.return_names, start=1):
            if ret_name in self.variable_table:
                last = self.variable_table[ret_name].versions
            else:
                last = 1
            exprs.append(f"output_{k} = {ret_name}[{last}]")

        expr_joined = " /\\\n    ".join(exprs)
        return f"predicate {self.name}({', '.join(params)}) =\n    (\n    {expr_joined}\n    )"

    def emit_call_line(self, input_exprs, output_names, array_param_names):
        """Return 'f(in..., out..., arrs...)' suitable for 'constraint ...;' usage."""
        args = []
        args += input_exprs
        args += output_names
        args += array_param_names
        return f"{self.name}({', '.join(args)})"