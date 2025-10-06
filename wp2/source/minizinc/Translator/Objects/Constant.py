from typing import Union
from Translator.Objects.DSTypes import DSList

class Constant:
    def __init__(self,
                 name: str,
                 value: str,
                 type_: Union[int, float, bool, DSList]):
        self.name = name
        self.value = value
        self.type = type_

    def to_minizinc(self) -> str:
        if isinstance(self.value, list):
            return f"array[1..{len(self.value)}] of int: {self.name} = [{', '.join(map(str, self.value))}]"
        print(f"Constant value type: {type(self.type).__name__}")
        print(f"Constant value type: {type(self.type)}")
        print(f"Constant value: {self.type}")
        return f"{self.type}: {self.name} = {self.value}"