import ast
from typing import Union
from Translator.Objects.DSTypes import DSList, compute_type

class Constant:
    def __init__(self,
                 name: str,
                 value: str = None,
                 type_: Union[int, float, bool, DSList] = "int"):
        self.name = name
        # Convert value to appropriate a numeral type if possible
        if value is not None:
            try:
                self.value = ast.literal_eval(value)
            except:
                raise ValueError(f"Unable to evaluate constant value: {value}")
        self.type = type_

    def to_minizinc(self) -> str:
        if isinstance(self.value, list):
            return f"array[1..{len(self.value)}] of int: {self.name} = [{', '.join(map(str, self.value))}]"
        print(f"Constant value type: {type(self.type).__name__}")
        print(f"Constant value type: {type(self.type)}")
        print(f"Constant value: {self.type}")
        return f"{self.type}: {self.name} = {self.value}"
    
    # def add_value(self, value: str):
    #     if self.value is not None and self.value != value:
    #         raise ValueError("Constant already has a different value.")
    #     self.value = value