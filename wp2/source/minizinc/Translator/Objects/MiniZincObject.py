import ast
from Translator.Objects.Predicate import Predicate
from Translator.Objects import Variable
from Translator.Objects.CodeBlock import CodeBlock
from Translator.Objects.Constant import Constant


class MiniZincObject:
    """
    Represents a Python class as a MiniZinc 'object':
      - class-level attributes -> MiniZinc constants
      - methods -> namespaced predicates: ClassName__method
    """

    def __init__(self, class_node: ast.ClassDef, predicates_registry: dict | None = None):
        self.node = class_node
        self.name = class_node.name
        self.predicates_registry = predicates_registry if predicates_registry is not None else {}
        self.methods: dict[str, Predicate] = {}   # method_name -> Predicate
        self.constants: dict[str, int | list[int]] = {}

        # 1) class-level assigns -> constants
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                cname = stmt.targets[0].id
                value = self._eval_simple_constant(stmt.value)
                if value is not None:
                    self.constants[cname] = value

        # 2) methods -> Predicates, namespaced as ClassName__method
        for stmt in class_node.body:
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name == "__init__":
                    initialisation = CodeBlock()
                    initialisation.run(stmt.body, loop_scope={})
                    print("Initialisation for", self.name, ":", initialisation.all_variable_declarations)
                    constants = []
                    for k, v in initialisation.symbol_table.items():
                        constants.append(Constant(k, v))
                    new_record = Record(f"{self.name}",
                                        list(initialisation.all_variable_declarations.values()),
                                        constants)
                    print("Emitting record definition for", self.name)
                    print(new_record.emit_definition())
                    print(initialisation.symbol_table)
                else:
                    ns_name = f"{self.name}__{stmt.name}"
                    print("Defining method predicate:", ns_name)
                    pred = Predicate(stmt, predicates=self.predicates_registry, name_override=ns_name)
                    self.methods[stmt.name] = pred
                    # also register into global registry if you want global lookup
                    self.predicates_registry[ns_name] = pred

    def _eval_simple_constant(self, node):
        """Very small evaluator for common literal class constants (int, list[int])."""
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.List) and all(isinstance(elt, ast.Constant) and isinstance(elt.value, int) for elt in node.elts):
            return [elt.value for elt in node.elts]
        return None

    def emit_symbol_declarations(self) -> list[str]:
        """Emit MiniZinc declarations for class-level constants."""
        decls = []
        for name, val in self.constants.items():
            qname = f"{self.name}__{name}"
            if isinstance(val, int):
                decls.append(f"int: {qname} = {val};")
            elif isinstance(val, list):
                decls.append(f"array[1..{len(val)}] of int: {qname} = [{', '.join(map(str, val))}];")
        return decls
