from Translator.Objects.DSTypes import compute_type


class Variable:
    """
    Minimal MiniZinc declaration:
      - name: variable name
      - type_: 'int' | 'float' | 'bool' (default 'int')
      - lower/upper: optional bounds
      - dims: None (scalar), int/str (1D length), or tuple[int|str,...] (multi-dim)
    """
    def __init__(self,
                 name,
                 type_="int",
                 versions=None,
                 annotation=None):
        self.name = name
        if annotation is not None:
            self.type = compute_type(annotation)
        else:
            self.type = type_
        self.versions = versions
        
    def _array_prefix(self):
        prefix = ""
        if self.versions is not None:
            prefix += f"array[{self._index_expr(self.versions)}] of "
        return prefix

    def _index_expr(self, d):
        return f"1..{d}" if isinstance(d, (int, str)) else str(d)

    def define_versions(self, versions):
        self.versions = versions

    def to_minizinc(self):
        if isinstance(self.type, str):
            return f"{self._array_prefix()}var {self.type}: {self.name}"
        else:
            return f"{self._array_prefix()}var {self.type.representation()}: {self.name}"

    def __str__(self):
            return self.to_minizinc()
        
    def __repr__(self):
        return f"Declaration({self.name!r}, type_={self.type!r}, versions={self.versions!r})"