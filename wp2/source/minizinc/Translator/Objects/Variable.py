from Translator.Objects.DSTypes import DSInt, compute_type


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
                 type_=None,
                 versions=None,
                 annotation=None,
                 known_types=None):
        self.name = name
        if annotation is not None:
            self.type = compute_type(annotation)
        else:
            self.type = compute_type(type_) if type_ is not None else DSInt()
        if self.type is None:
            self.representation_type_with_vars = "var int"
        elif isinstance(self.type, str):  # TODO if is str compute real type earlier
            self.representation_type_with_vars = f"var {compute_type(self.type).representation()}"
        else:
            self.representation_type_with_vars = self.type.representation(with_vars=True, known_types=known_types)
        self.versions = versions

        # TODO from each type, we can create an object indicating which of its fields have already been assigned
        self.assigned_fields = self.type.assigned_fields(known_types=known_types)
        
    def _array_prefix(self):
        prefix = ""
        if self.versions is not None:
            prefix += f"array[{self._index_expr(self.versions)}] of "
        return prefix

    def _index_expr(self, d):
        return f"1..{d}" if isinstance(d, (int, str)) else str(d)

    def define_versions(self, versions):
        self.versions = versions

    def define_type(self, type_):
        self.type = type_

    def to_minizinc(self):
        return f"{self._array_prefix()}{self.representation_type_with_vars}: {self.name}"
        
    def versioned_name(self):
        return f"{self.name}[{self.versions}]"

    def __str__(self):
            return self.to_minizinc()
        
    def __repr__(self):
        return f"Declaration({self.name!r}, type_={self.type!r}, versions={self.versions!r})"