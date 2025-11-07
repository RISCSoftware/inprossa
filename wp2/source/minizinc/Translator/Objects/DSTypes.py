"""
Types in DSL

Types will optionally have names
They will have a representation and a var_representation, to refer to variables in function definitions and constants, and to refer to generic variables respectively.
They will have a method to emit their definition given their name.
They will have a method to create the list of constraints that is forced when one of the variables of that type is assigned. This method takes as input the variable name, the right hand side, the assigned fields of that variable and the access chain, for example, [3,".length", ".ver", 5, 4] in my_var[3].length.ver[5][4]
Further, lists will have a type:DS.. and a length:int
And Records will have a dict of field_name:str -> field_type:DS...
"""
import ast
from typing import Optional, Union, Dict
from Translator.Tools import ast_to_evaluation_constants


def remove_ast(input, constant_table: Optional[dict] = None):
    print("Removing AST from input:", input, type(input), ast.dump(input) if isinstance(input, ast.AST) else "N/A")
    if isinstance(input, ast.Name):
        if constant_table is not None and input.id in constant_table:
            return constant_table[input.id]
        return input.id
    # If constant and no numerical value, return value
    if isinstance(input, ast.Constant):
        if isinstance(input.value, (int, float, str)):
            pass
        return input.value
    return input
# Do I need names in types?
# Because when they're defined we do
# type MyInt = DSInt(0,10)
# then later we can just use MyInt
class DSInt:
    def __init__(self,
                 lb: Union[int, str] = None,
                 ub: Union[int, str] = None,
                 name: str = None,
                 known_types: Optional[set] = set(),
                 constant_table: Optional[dict] = None
                 ):
        self.known_types = known_types
        self.lb = ast_to_evaluation_constants(lb, constant_table=constant_table)
        self.ub = ast_to_evaluation_constants(ub, constant_table=constant_table)
        if name is None:
            self.name = self.representation()
        else:
            self.name = name
        self.var_name = f"var {self.name}"

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration

    def representation(self, with_vars=False):
        if with_vars:
            representation = "var "
        else:
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

    def initial_assigned_fields(self):
        return 0

class DSFloat:
    def __init__(self,
                 lb: Union[float, str] = None,
                 ub: Union[float, str] = None,
                 name: str = None,
                 known_types: Optional[set] = set(),
                 constant_table: Optional[dict] = None
                 ):
        self.known_types = known_types
        self.lb = ast_to_evaluation_constants(lb, constant_table=constant_table)
        self.ub = ast_to_evaluation_constants(ub, constant_table=constant_table)
        if name is None:
            self.name = self.representation()
        else:
            self.name = name
        self.var_name = f"var {self.name}"

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration
    
    def representation(self, with_vars=False):
        if with_vars:
            representation = "var "
        else:
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

    def initial_assigned_fields(self):
        return 0


class DSBool:
    def __init__(self, name: str = None,
                 known_types: Optional[set] = set(),
                 constant_table: Optional[dict] = None
                 ):
        self.known_types = known_types
        if name is None:
            self.name = self.representation()
        else:
            self.name = name
        self.var_name = f"var {self.name}"

    def emit_definition(self):
        return f"type {self.name} = bool"

    def representation(self, with_vars=False):
        if with_vars:
            return "var bool"
        return "bool"
    def initial_assigned_fields(self):
        return 0

class DSList:
    def __init__(self,
                 length: Union[int, str],
                 elem_type: type = DSInt(),
                 name: str = None,
                 known_types: Optional[set] = set(),
                 constant_table: Optional[dict] = None
                 ):
        self.known_types = known_types
        print("Constant table: ", constant_table)
        self.length = ast_to_evaluation_constants(length, constant_table=constant_table)
        self.elem_type = compute_type(
            elem_type,
            known_types=known_types,
            constant_table=constant_table
            )
        if name is None:
            self.name = self.representation()
            self.var_name = self.representation(with_vars=True)
        else:
            self.name = name
            self.var_name = f"var {self.name}"

    def representation(self, with_vars=False):
        representation = f"array[1..{self.length}] of "
        type_repr = compute_type(self.elem_type, known_types=self.known_types)
        if with_vars:
            representation += type_repr.representation(with_vars=True)
        else:
            representation += type_repr.name
        return representation

    def emit_definition(self):
        declaration = f"type {self.name} = {self.representation()}"
        return declaration

    def initial_assigned_fields(self):
        print("LLength:", self.length)
        return [self.elem_type.initial_assigned_fields() for _ in range(self.length)]

class DSRecord:
    def __init__(self,
                 fields: Dict[str, type],
                 name: str = None,
                 known_types: Optional[set] = set(),
                 constant_table: Optional[dict] = None
                 ):
        self.known_types = known_types
        self.constant_table = constant_table
        self.types_dict = type_dict_from_ast_literal(
            fields,
            known_types=known_types,
            constant_table=constant_table
            )
        if name is None:
            self.name = self.representation()
            self.var_name = self.representation(with_vars=True)
        else:
            self.name = name
            self.var_name = f"var {self.name}"

    def fields_declarations(self):
        field_defs = []
        for fname, ftype in self.types_dict.items():
            field_defs.append(f"{ftype.name}: {fname}")
        fields_str = ",\n    ".join(field_defs)
        return fields_str
    
    def representation(self, with_vars=False):
        self.fields_declar = self.fields_declarations()
        repre = ""
        if with_vars:
            repre += "var "
        return f"{repre}record(\n    {self.fields_declar}\n)"

    def emit_definition(self):
        return f"type {self.name} = {self.representation()}"
    
    def initial_assigned_fields(self):
        return {fname: compute_type(ftype).initial_assigned_fields() for fname, ftype in self.types_dict.items()}

class DSType:
    def __init__(self,
                 type_node: ast.Call,
                 type_name: str = None,
                 known_types: Optional[set] = None,
                 constant_table: Optional[dict] = None):
        self.name = type_name
        self.type_node = type_node
        self.type_object_name = type_node.func.id
        print("Constant table in DSType:", constant_table)
        self.positional_args = [remove_ast(arg) for arg in type_node.args]
        self.arguments = {kw.arg: kw.value for kw in type_node.keywords}
        # Call the function to parse arguments
        if self.type_object_name == "DSInt":
            self.type_obj = DSInt(name=self.name, *self.positional_args, **self.arguments, known_types=known_types, constant_table=constant_table)
        elif self.type_object_name == "DSFloat":
            self.type_obj = DSFloat(name=self.name, *self.positional_args, **self.arguments, known_types=known_types, constant_table=constant_table)
        elif self.type_object_name == "DSBool":
            self.type_obj = DSBool(name=self.name, *self.positional_args, **self.arguments, known_types=known_types, constant_table=constant_table)
        elif self.type_object_name == "DSList":
            self.type_obj = DSList(name=self.name, *self.positional_args, **self.arguments, known_types=known_types, constant_table=constant_table)
        elif self.type_object_name == "DSRecord":
            self.type_obj = DSRecord(name=self.name, *self.positional_args, **self.arguments, known_types=known_types, constant_table=constant_table)

    def return_type(self):
        return self.type_obj


def dict_from_ast_literal(node: ast.AST,
                          known_types = set()) -> dict:
    """
    Convert an ast.Dict consisting only of literal keys/values
    into a Python dict. Raises on **unpacking and non-literals.
    """
    if not isinstance(node, ast.Dict):
        raise TypeError("Expected ast.Dict")

    out = {}
    for k_node, v_node in zip(node.keys, node.values):
        if k_node is None:  # {**something}
            raise ValueError("Dict unpacking (**x) not supported")

        try:
            key = ast.literal_eval(k_node)   # e.g., "name", 1, (1,2)
        except Exception as e:
            raise ValueError(f"Non-literal dict key: {ast.dump(k_node)}") from e

        if hasattr(v_node, 'id') and (v_node.id in minizinc_original_types or v_node.id in known_types):
            val = v_node.id
        elif isinstance(v_node, ast.Call):
            # e.g., DSInt(0, 10), DSList(7, DSInt(0, 10))
            v_node_type = compute_type(v_node)  # validate
            type_def = v_node_type.emit_definition(known_types)  # validate
            val = type_def
        else:
            try:
                val = ast.literal_eval(v_node)   # e.g., "string", 3, True
            except Exception as e:
                raise ValueError(f"Non-literal dict value for key {key}: {ast.dump(v_node)}") from e

        out[key] = val
    return out


def compute_type(
        type_node: Union[ast.Call, ast.Name],
        type_name: str = None,
        known_types: Optional[set] = None,
        constant_table: Optional[dict] = None
        ) -> DSType:
    if isinstance(type_node, (DSInt, DSFloat, DSBool, DSList, DSRecord)):
        returned_type = type_node
        return returned_type
    if isinstance(type_node, str) and type_name is None:
        # Already a string type name
        if type_node == "int":
            returned_type = DSInt(name=type_node, constant_table=constant_table)
            return returned_type
        elif type_node == "float":
            returned_type = DSFloat(name=type_node, constant_table=constant_table)
            return returned_type
        elif type_node == "bool":
            returned_type = DSBool(name=type_node, constant_table=constant_table)
            return returned_type
        else:
            if known_types is not None and type_node in known_types:
                returned_type = known_types[type_node]
                return returned_type
            else:
                raise ValueError(f"Unknown type string: {type_node}")
    if isinstance(type_node, ast.Name):
        # int, float, bool or an existing type
        returned_type = compute_type(type_node.id, type_name=type_name, known_types=known_types)
        return returned_type
    if isinstance(type_node, ast.Call):
        # A DS type constructor call
        returned_type = DSType(type_node, type_name, known_types=known_types, constant_table=constant_table).return_type()
        return returned_type
    if isinstance(type_node, ast.Constant):
        # A constant type name
        if isinstance(type_node.value, str):
            returned_type = compute_type(type_node.value, type_name=type_name, known_types=known_types, constant_table=constant_table)
            return returned_type
        else:
            raise ValueError(f"Unsupported constant type node: {type_node.value}")
    raise ValueError(f"Unsupported type node: {type_node}")

minizinc_original_types = {
    "int",
    "float",
    "string",
    "bool",
}

def type_dict_from_ast_literal(node: ast.AST,
                               known_types = set(),
                               constant_table = dict()) -> dict:
    out = {}
    for k_node, v_node in zip(node.keys, node.values):
        key = ast.literal_eval(k_node)
        v_node_type = compute_type(v_node, known_types=known_types, constant_table=constant_table)  # validate
        out[key] = v_node_type
    return out


def dict_from_ast_literal(node: ast.AST,
                          known_types = set()) -> dict:
    """
    Convert an ast.Dict consisting only of literal keys/values
    into a Python dict. Raises on **unpacking and non-literals.
    """
    if not isinstance(node, ast.Dict):
        raise TypeError("Expected ast.Dict")

    out = {}
    for k_node, v_node in zip(node.keys, node.values):
        if k_node is None:  # {**something}
            raise ValueError("Dict unpacking (**x) not supported")

        try:
            key = ast.literal_eval(k_node)   # e.g., "name", 1, (1,2)
        except Exception as e:
            raise ValueError(f"Non-literal dict key: {ast.dump(k_node)}") from e

        if hasattr(v_node, 'id') and (v_node.id in minizinc_original_types or v_node.id in known_types):
            val = v_node.id
        elif isinstance(v_node, ast.Call):
            # e.g., DSInt(0, 10), DSList(7, DSInt(0, 10))
            v_node_type = compute_type(v_node)  # validate
            type_def = v_node_type.representation(known_types)  # validate
            val = type_def
        else:
            try:
                val = ast.literal_eval(v_node)   # e.g., "string", 3, True
            except Exception as e:
                raise ValueError(f"Non-literal dict value for key {key}: {ast.dump(v_node)}") from e

        out[key] = val
    return out