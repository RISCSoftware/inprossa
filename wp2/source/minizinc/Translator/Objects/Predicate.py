import ast
from Translator.Objects.CodeBlock import CodeBlock

    
class Predicate(CodeBlock):
    """Translate a Python function into a MiniZinc predicate."""
    def __init__(self, func_node: ast.FunctionDef, predicates=None, name_override: str | None = None):
        super().__init__(symbol_table=None, predicates=predicates)
        self.func_node = func_node
        self.name = name_override if name_override is not None else func_node.name
        self.input_names = [a.arg for a in func_node.args.args]
        self.n_inputs = len(self.input_names)
        self.return_names = self._extract_return_names(func_node)
        self.n_outputs = len(self.return_names)

        # Execute function body to collect constraints and versioning
        func_body = [s for s in func_node.body if not isinstance(s, ast.Return)]
        print("Processing predicate:", self.name)
        self.run(func_body, loop_scope={})
        print("Finished processing predicate:", self.name)

        # Ensure inputs have at least one version and will be tied to input_i
        for i_name in self.input_names:
            if i_name not in self.variable_index:
                print("Input", i_name, "not assigned in body, adding initial version.")
                self.new_evolving_variable(i_name)

        # Internal arrays order and sizes (stable ordering)

        self.arrays_order = sorted(self.all_variable_declarations.keys())

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
            params += [self.all_variable_declarations[v].to_minizinc()[:-1]]  # remove trailing ';'

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