class Declaration:
    """
    Minimal MiniZinc declaration:
      - name: variable name
      - type_: 'int' | 'float' | 'bool' (default 'int')
      - lower/upper: optional bounds
      - dims: None (scalar), int/str (1D length), or tuple[int|str,...] (multi-dim)
    """
    def __init__(self, name, type_="int", lower=None, upper=None, dims=None, versions=None, domain=None):
        self.name = name
        self.type = type_
        self.lower = lower
        self.upper = upper
        self.dims = dims
        self.versions = versions
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
        prefix = ""
        if self.versions is not None:
            prefix += f"array[{self._index_expr(self.versions)}] of "
        if isinstance(self.dims, (int, str)):
            prefix += f"array[{self._index_expr(self.dims)}] of "
        elif isinstance(self.dims, (list, tuple)):
            idxs = "] of array[".join(self._index_expr(d) for d in self.dims)
            prefix += f"array[{idxs}] of "
        return prefix

    def define_versions(self, versions):
        self.versions = versions

    def define_dims(self, dims):
        self.dims = dims

    def to_minizinc(self):
        return f"{self._array_prefix()}{self._elem_type()}: {self.name}"

    def __str__(self):
        return self.to_minizinc()
    
    def __repr__(self):
        return f"Declaration({self.name!r}, type_={self.type!r}, lower={self.lower}, upper={self.upper}, dims={self.dims})"