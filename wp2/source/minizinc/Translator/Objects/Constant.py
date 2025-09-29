class Constant:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def to_minizinc(self) -> str:
        if isinstance(self.value, list):
            return f"array[1..{len(self.value)}] of int: {self.name} = [{', '.join(map(str, self.value))}]"
        return f"{type(self.value).__name__}: {self.name} = {self.value}"