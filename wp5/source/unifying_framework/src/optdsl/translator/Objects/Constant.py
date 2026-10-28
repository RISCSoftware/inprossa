import ast
from typing import Union
from src.optdsl.translator.Objects.DSTypes import DSList, DSRecord
from src.optdsl.translator.helper_tools import ast_to_object, ExpressionRewriter


class Constant:
    def __init__(
        self,
        name: str,
        stmt_value: str = None,
        type_: Union[int, float, bool, DSList] = "int",
        code_block=None,
        loop_scope=None,
    ):
        self.code_block = code_block
        self.name = name
        self.type = type_
        self.loop_scope = {} if loop_scope is None else loop_scope
        self.empty_structure = self.build_empty_structure(self.type)
        self.value_structure = self.fill_structure(self.empty_structure, stmt_value)

    def to_minizinc(self) -> str:
        return f"{self.type.name}: {self.name} = {self._to_mzn(self.value_structure)}"

    def _is_empty_filler(self, value) -> bool:
        """True if ``value`` is an empty structure produced by padding a
        shorter DSL literal to the declared DS type length (never supplied
        by the user), so it should be omitted from the MiniZinc output."""
        if isinstance(value, dict):
            return all(self._is_empty_filler(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return len(value) == 0 or all(self._is_empty_filler(v) for v in value)
        return value is None

    def _to_mzn(self, value):
        """Recursively convert stored Python structures to MiniZinc text.

        ``None`` marks a field/element that was never filled from the DSL
        literal (e.g. a ``DSList`` declared longer than its literal).  Such
        sentinel values are never valid MiniZinc, so they are dropped:
          - for a list/tuple we trim the trailing empty elements (a MiniZinc
            array literal doesn't need padding to the declared length), and
          - any ``None`` that remains (e.g. inside a record) is skipped.
        """
        if isinstance(value, dict):
            fields = []
            for k, v in value.items():
                rendered = self._to_mzn(v)
                if rendered is None:
                    continue
                fields.append(f"{k}: {rendered}")
            if not fields:
                return None
            return f"({', '.join(fields)})"
        elif isinstance(value, (list, tuple)):
            elems = [self._to_mzn(v) for v in value]
            while elems and elems[-1] is None:
                elems.pop()
            return f"[{', '.join(elems)}]"
        elif value is None:
            return None
        elif isinstance(value, str):
            return f"{value}"
        else:
            return str(value)

    def build_empty_structure(self, ds_type):
        """
        Build a Python structure matching the DS type shape.
        DSRecord -> dict of fields
        DSList   -> list of elements
        Base types -> None
        """

        if isinstance(ds_type, DSRecord):
            return {
                k: self.build_empty_structure(v) for k, v in ds_type.types_dict.items()
            }
        elif isinstance(ds_type, DSList):  # DSList
            return [
                self.build_empty_structure(ds_type.elem_type)
                for _ in range(ds_type.length)
            ]
        else:
            return None

    def fill_structure(self, target, value_node):
        """
        Recursively fill a pre-built DSRecord/DSList structure (target)
        from an AST node representing dicts/lists/constants.
        """
        if value_node is None:
            return target
        # --- 1. Dicts: e.g. {"x":1,"y":2}
        elif isinstance(value_node, ast.Dict):
            for key_node, val_node in zip(value_node.keys, value_node.values):
                # extract key name (must be str constant or name)
                if isinstance(key_node, ast.Constant):
                    key = key_node.value
                elif isinstance(key_node, ast.Name):
                    key = key_node.id
                else:
                    raise TypeError(f"Unsupported dict key type: {type(key_node)}")

                if isinstance(target, dict) and key in target:
                    target[key] = self.fill_structure(target[key], val_node)
            return target

        # --- 2. Lists or tuples: e.g. [1,2,3] or [(x:1), (x:2)]
        elif isinstance(value_node, (ast.List, ast.Tuple)):
            if not isinstance(target, list):
                raise TypeError("Expected list target for list AST node")
            for i, elem_node in enumerate(value_node.elts):
                if i < len(target):
                    target[i] = self.fill_structure(target[i], elem_node)
            return target
        # --- 3. Constants or other expressions
        else:
            if self.empty_structure is None:
                # It's a base type constant
                evaluation = ExpressionRewriter(
                    self.loop_scope, code_block=self.code_block
                ).get_expr_value(value_node)
            else:
                # It's a structure assignment
                evaluation = ExpressionRewriter(
                    self.loop_scope, code_block=self.code_block
                ).rewrite_expr(value_node)
            return evaluation

    def assign_chain(self, structure, chain, value):
        """
        Recursively assign `value` into a nested structure (dict/list)
        following a key/index chain where each step is a tuple:
            ("dict", key)  or  ("list", index)

        Supports partial record updates like:
            assign_chain(fam, [("dict","father")], {"name":"Peter","age":23})
            assign_chain(fam, [("dict","children"),("list",1),("dict","age")], 12)
        """
        if isinstance(value, ast.Tuple):
            value = value.elts[0]
        value = ast_to_object(value)
        if not chain:
            # merge or overwrite directly
            if isinstance(structure, dict) and isinstance(value, dict):
                for k, v in value.items():
                    self.assign_chain(structure, [("dict", k)], v)
            elif isinstance(structure, list) and isinstance(value, list):
                for i, v in enumerate(value):
                    if i < len(structure):
                        self.assign_chain(structure, [("list", i)], v)
            else:
                return value
            return structure

        (kind, key), *rest = chain

        # descend into substructure
        if kind == "dict":
            if not isinstance(structure, dict):
                raise TypeError(f"Expected dict at this step, got {type(structure)}")
            if key not in structure:
                structure[key] = {} if rest else None
            structure[key] = self.assign_chain(structure[key], rest, value)

        elif kind == "list":
            if not isinstance(structure, list):
                raise TypeError(f"Expected list at this step, got {type(structure)}")
            if key >= len(structure):
                raise IndexError(
                    f"List index {key} out of range (len={len(structure)})"
                )
            structure[key] = self.assign_chain(structure[key], rest, value)

        else:
            raise ValueError(f"Invalid chain kind: {kind}")

        return structure
