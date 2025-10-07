"""
Types in DSL
"""
import ast
from typing import Optional, Union, Dict
from Translator.Tools import dict_from_ast_literal

class DSInt:
    def __init__(self,
                 lb: Union[int, str] = None,
                 ub: Union[int, str] = None,
                 name: str = None):
        self.lb = remove_ast(lb)
        self.ub = remove_ast(ub)
        if name is None:
            self.name = self.representation()
        else:
            self.name = name

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration

    def representation(self):
        representation = ""
        if self.lb is None and self.ub is None:
            representation += "int"
            return representation
        if self.lb is not None:
            representation += f"{self.lb}"
        representation += ".."
        if self.ub is not None:
            representation += f"{self.ub}"
        return representation

class DSFloat:
    def __init__(self,
                 lb: Union[float, str] = None,
                 ub: Union[float, str] = None,
                 name: str = None):
        self.lb = remove_ast(lb)
        self.ub = remove_ast(ub)
        if name is None:
            self.name = self.representation()
        else:
            self.name = name

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration
    
    def representation(self):
        representation = ""
        if self.lb is None and self.ub is None:
            representation += "float"
            return representation
        if self.lb is not None:
            representation += f"{self.lb}"
        representation += ".."
        if self.ub is not None:
            representation += f"{self.ub}"
        return representation


class DSBool:
    def __init__(self, name: str = None):
        if name is None:
            self.name = self.representation()
        else:
            self.name = name

    def emit_definition(self):
        return f"type {self.name} = bool"

    def representation(self):
        return "bool"

class DSList:
    def __init__(self,
                 length: Union[int, str],
                 elem_type: type = None,
                 name: str = None
                 ):
        self.name = name
        self.length = remove_ast(length)
        self.elem_type = elem_type

    def representation(self):
        representation = f"array[1..{self.length}] of "
        if self.elem_type is not None:
            type_repr = compute_type(self.elem_type)
            if isinstance(type_repr, str):
                representation += type_repr
            else:
                representation += compute_type(self.elem_type).representation()
        else:
            # default to int if not specified
            representation += "int"
        return representation

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration

class DSRecord:
    def __init__(self,
                 fields: Dict[str, type],
                 name: str = None):
        self.name = name
        self.ast_fields = fields

    def fields_declarations(self):
        self.fields = dict_from_ast_literal(self.ast_fields, self.known_types)
        field_defs = []
        for fname, ftype in self.fields.items():
            field_defs.append(f"{ftype}: {fname}")
        fields_str = ",\n    ".join(field_defs)
        return fields_str
    
    def representation(self):
        return f"record(\n    {self.fields_declarations}\n)"

    def emit_definition(self, known_types: Optional[set] = None):
        self.known_types = known_types if known_types is not None else set()
        self.fields_declarations = self.fields_declarations()
        return f"type {self.name} = {self.representation()}"

class DSType:
    def __init__(self,
                 type_node: ast.Call,
                 type_name: str = None):
        self.name = type_name
        self.type_node = type_node
        self.type_object_name = type_node.func.id
        self.positional_args = [remove_ast(arg) for arg in type_node.args]
        self.arguments = {kw.arg: kw.value for kw in type_node.keywords}
        # Call the function to parse arguments
        if self.type_object_name == "DSInt":
            self.type_obj = DSInt(name=self.name, *self.positional_args, **self.arguments)
        elif self.type_object_name == "DSFloat":
            self.type_obj = DSFloat(name=self.name, *self.positional_args, **self.arguments)
        elif self.type_object_name == "DSBool":
            self.type_obj = DSBool(name=self.name, *self.positional_args, **self.arguments)
        elif self.type_object_name == "DSList":
            self.type_obj = DSList(name=self.name, *self.positional_args, **self.arguments)
        elif self.type_object_name == "DSRecord":
            self.type_obj = DSRecord(name=self.name, *self.positional_args, **self.arguments)

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

def compute_type(
        type_node: Union[ast.Call, ast.Name],
        type_name: str = None
        ) -> DSType:
    if isinstance(type_node, str) and type_name is None:
        # Already a string type name
        if type_node == "int":
            return DSInt(name=type_node)
        elif type_node == "float":
            return DSFloat(name=type_node)
        elif type_node == "bool":
            return DSBool(name=type_node)
        else:
            raise ValueError(f"Unknown type string: {type_node}")
    if isinstance(type_node, ast.Name):
        # int, float, bool or an existing type
        return type_node.id
    if isinstance(type_node, ast.Call):
        # A DS type constructor call
        return DSType(type_node, type_name).type_obj
    raise ValueError(f"Unsupported type node: {type_node}")
