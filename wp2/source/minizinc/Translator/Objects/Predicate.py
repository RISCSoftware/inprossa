import ast
from Translator.Objects.CodeBlock import CodeBlock

    
class Predicate(CodeBlock):
    """Translate a Python function into a MiniZinc predicate."""
    def __init__(self, func_node: ast.FunctionDef):
        super().__init__(symbol_table=None, predicates=None)
        self.func_node = func_node
        self.name = func_node.name
        self.input_names = [a.arg for a in func_node.args.args]
        self.n_inputs = len(self.input_names)
        self.return_names = self._extract_return_names(func_node)
        self.n_outputs = len(self.return_names)

        # Execute function body to collect constraints and versioning
        body_wo_return = [s for s in func_node.body if not isinstance(s, ast.Return)]
        self.run(body_wo_return, loop_scope={})

        # Ensure inputs have at least one version and will be tied to input_i
        for i_name in self.input_names:
            if i_name not in self.variable_index:
                self.variable_index[i_name] = 1
                self.variable_declarations[i_name] = ("int", None)

        # Internal arrays order and sizes (stable ordering)
        self.arrays_order = sorted(self.variable_index.keys())
        self.local_array_sizes = {v: self.variable_index[v] for v in self.arrays_order}

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
        # Parameters: inputs, outputs, then arrays in arrays_order
        params = []
        # inputs
        params += [f"int: input_{i+1}" for i in range(self.n_inputs)]
        # outputs
        params += [f"var int: output_{i+1}" for i in range(self.n_outputs)]
        # arrays (as var int arrays)
        for v in self.arrays_order:
            size = self.local_array_sizes[v]
            params += [f"array[1..{size}] of var int: {v}"]

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
            last = self.variable_index.get(ret_name, 1)
            exprs.append(f"output_{k} = {ret_name}[{last}]")

        expr_joined = " /\\\n    ".join(exprs)
        return f"predicate {self.name}({', '.join(params)}) =\n    (\n    {expr_joined}\n    );"

    def emit_call_line(self, input_exprs, output_names, array_param_names):
        """Return 'f(in..., out..., arrs...)' suitable for 'constraint ...;' usage."""
        args = []
        args += input_exprs
        args += output_names
        args += array_param_names
        return f"{self.name}({', '.join(args)})"