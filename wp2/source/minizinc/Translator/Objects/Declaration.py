class Declaration:
    """
    Minimal MiniZinc declaration:
      - name: variable name
      - type_: 'int' | 'float' | 'bool' (default 'int')
      - lower/upper: optional bounds
      - dims: None (scalar), int/str (1D length), or tuple[int|str,...] (multi-dim)
    """
    def __init__(self, name, type_="int", lower=None, upper=None, dims=None, domain=None):
        self.name = name
        self.type = type_
        self.lower = lower
        self.upper = upper
        self.dims = dims
        if domain is not None:
            self.lower, self.upper = domain

    def _elem_type(self):
        if self.lower is not None and self.upper is not None:
            return f"var {self.lower}..{self.upper}"
        else:
            return f"var {self.type}"

    def _index_expr(self, d):
        return f"1..{d}" if isinstance(d, (int, str)) else str(d)

    def _array_prefix(self):
        if self.dims is None:
            return ""
        if isinstance(self.dims, (int, str)):
            return f"array[{self._index_expr(self.dims)}] of "
        idxs = ", ".join(self._index_expr(d) for d in self.dims)
        return f"array[{idxs}] of "

    def define_size(self, size):
        self.dims = size

    def to_minizinc(self):
        return f"{self._array_prefix()}{self._elem_type()}: {self.name};"

    def __str__(self):
        return self.to_minizinc()
    
    def __repr__(self):
        return f"Declaration({self.name!r}, type_={self.type!r}, lower={self.lower}, upper={self.upper}, dims={self.dims})"