"""
Types in DSL
"""
import ast
from typing import Optional, Union, Dict
from Translator.Tools import dict_from_ast_literal

class DSInt:
    def __init__(self,
                 lb: Union[int, str] = None,
                 ub: Union[int, str] = None):
        self.lb = remove_ast(lb)
        self.ub = remove_ast(ub)

    def emit_definition(self, name: str):
        declaration = f"type {name} = "
        if self.lb is None and self.ub is None:
            declaration += "int"
            return declaration
        if self.lb is not None:
            declaration += f"{self.lb}"
        declaration += ".."
        if self.ub is not None:
            declaration += f"{self.ub}"
        return declaration

class DSFloat:
    def __init__(self,
                 lb: Union[float, str] = None,
                 ub: Union[float, str] = None):
        self.lb = remove_ast(lb)
        self.ub = remove_ast(ub)

    def emit_definition(self, name: str):
        declaration = f"type {name} = "
        if self.lb is None and self.ub is None:
            declaration += "float"
            return declaration
        if self.lb is not None:
            declaration += f"{self.lb}"
        declaration += ".."
        if self.ub is not None:
            declaration += f"{self.ub}"
        return declaration

class DSBool:
    def __init__(self):
        pass

    def emit_definition(self, name: str):
        return f"type {name} = bool"

class DSList:
    def __init__(self,
                 length: Union[int, str],
                 elem_type: type = None
                 ):
        self.length = remove_ast(length)
        self.elem_type = elem_type

    def emit_definition(self, name: str):
        declaration = f"type {name} = array[1..{self.length}] of "
        if self.elem_type is not None:
            declaration += self.elem_type.id
        else:
            # default to int if not specified
            declaration += "int"
        return declaration

class DSRecord:
    def __init__(self,
                 fields: Dict[str, type]):
        self.ast_fields = fields

    def fields_declarations(self):
        self.fields = dict_from_ast_literal(self.ast_fields, self.known_types)
        field_defs = []
        for fname, ftype in self.fields.items():
            field_defs.append(f"{ftype}: {fname}")
        fields_str = ",\n    ".join(field_defs)
        return fields_str

    def emit_definition(self, name, known_types: Optional[set] = None):
        self.known_types = known_types if known_types is not None else set()
        self.fields_declarations = self.fields_declarations()
        return f"type {name} = record(\n    {self.fields_declarations}\n)"

class DSType:
    def __init__(self,
                 type_node: ast.Call):
        self.type_node = type_node
        self.type_name = type_node.func.id
        self.positional_args = [remove_ast(arg) for arg in type_node.args]
        self.arguments = {kw.arg: kw.value for kw in type_node.keywords}
        # Call the function to parse arguments
        if self.type_name == "DSInt":
            self.type_obj = DSInt(*self.positional_args, **self.arguments)
        elif self.type_name == "DSFloat":
            self.type_obj = DSFloat(*self.positional_args, **self.arguments)
        elif self.type_name == "DSBool":
            self.type_obj = DSBool(*self.positional_args, **self.arguments)
        elif self.type_name == "DSList":
            self.type_obj = DSList(*self.positional_args, **self.arguments)
        elif self.type_name == "DSRecord":
            self.type_obj = DSRecord(*self.positional_args, **self.arguments)
    
    def return_type(self):
        return self.type_obj

def remove_ast(input):
    if isinstance(input, ast.Name):
        return input.id
    # If constant and no numerical value, return value
    if isinstance(input, ast.Constant):
        if isinstance(input.value, (int, float, str)):
            pass
        return input.value
    return input
