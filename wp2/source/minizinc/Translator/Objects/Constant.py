import ast
from typing import Union
from Translator.Objects.DSTypes import DSList, compute_type

class Constant:
    def __init__(self,
                 name: str,
                 value: str = None,
                 type_: Union[int, float, bool, DSList] = "int",
                 code_block = None,
                 loop_scope = {}):
        self.name = name
        # Convert value to appropriate a numeral type if possible
        if value is not None:
            tree = ast.parse(value, mode='eval')
            try:
                rewritten = code_block.rewrite_expr(tree, get_numeral = True, loop_scope=loop_scope)
                self.value = self.to_number(rewritten)
            except:
                self.value = value
        else:
            self.value = value
        self.type = type_

    def to_minizinc(self) -> str:
        if hasattr(self.type, 'length'):
            return f"array[1..{self.type.length}] of int: {self.name} = {self.value}"
        return f"{self.type}: {self.name} = {self.value}"
    
    # def add_value(self, value: str):
    #     if self.value is not None and self.value != value:
    #         raise ValueError("Constant already has a different value.")
    #     self.value = value

    def to_number(self, s):
        # Try to convert to int if possible, otherwise float
        try:
            return int(s)
        except ValueError:
            return float(s)