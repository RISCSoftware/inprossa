import ast

from Translator.Objects.DSTypes import compute_type


minizinc_original_types = {
    "int",
    "float",
    "string",
    "bool",
}

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