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
            self.representation_type_with_vars = self.type.representation(with_vars=True)
        self.versions = versions

        # TODO from each type, we can create an object indicating which of its fields have already been assigned
        self.assigned_fields = self.type.initial_assigned_fields()
        
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
    
    def collect_assigned_chains(self, assigned_fields, prefix=None):
        """
        Returns a list of access chains (lists) that end in a value == 1.
        Example: {'a':[0,1], 'b':0} -> [['a', 1]]
        """
        if prefix is None:
            prefix = []
        chains = []

        if isinstance(assigned_fields, int):
            if assigned_fields == 1:
                chains.append(prefix)
            return chains

        if isinstance(assigned_fields, list):
            for idx, val in enumerate(assigned_fields):
                chains.extend(self.collect_assigned_chains(val, prefix + [idx]))
            return chains

        if isinstance(assigned_fields, dict):
            for key, val in assigned_fields.items():
                chains.extend(self.collect_assigned_chains(val, prefix + [f"{key}"]))
            return chains

        raise TypeError(f"Unsupported assigned_fields type: {type(assigned_fields)}")
    
    def is_chain_unassigned(self, access_chain):
        """
        Returns True if the path specified by `access_chain`
        is marked as assigned (1) in `assigned_fields`.
        """
        target = self.assigned_fields
        for step in access_chain:
            if isinstance(target, dict):
                if step not in target:
                    raise KeyError(f"Field '{step}' not found in assigned_fields.")
                target = target[step]
            elif isinstance(target, list):
                if not isinstance(step, int):
                    raise TypeError(f"Invalid list index: {step}")
                if step < 0 or step >= len(target):
                    raise IndexError(f"Index {step} out of range")
                target = target[step]
            else:
                raise TypeError(f"Invalid access step: {step}")
            
        
        return self.all_unassigned_recursive(target)
    
    def all_unassigned_recursive(self, value):
        """Check if all nested lists/dicts are marked as 1."""
        if isinstance(value, int):
            return value == 0
        if isinstance(value, list):
            return all(self.all_unassigned_recursive(v) for v in value)
        if isinstance(value, dict):
            return all(self.all_unassigned_recursive(v) for v in value.values())
        raise TypeError(f"Unsupported value type in assignment: {type(value)}")

    def mark_assigned_field(self, access_chain,
                            target = None):
        """
        Modifies `assigned_fields` setting the path specified
        by `access_chain` to 1. If the access ends at a container
        (list/dict), all its elements inside are set to 1 recursively.
        """
        if target is None:
            target = self.assigned_fields
        
        if access_chain != []:
            step = access_chain.pop(0)
            # --- Attribute (record field) access ---
            if isinstance(target, dict):
                if step not in target:
                    raise KeyError(f"Field '{step}' not found in assigned_fields.")
                target[step] = self.mark_assigned_field(access_chain, target[step])
                return target
            elif isinstance(target, list):
                if not isinstance(step, int):
                    raise TypeError(f"Invalid list index: {step}")
                if step < 0 or step >= len(target):
                    raise IndexError(f"Index {step} out of range")
                target[step] = self.mark_assigned_field(access_chain, target[step])
                return target
            else:
                raise TypeError(f"Invalid access step: {step}")
        
        else:
            # Now assigned fields inside target should be marked as 1
            self._mark_all_recursive_inplace(target)

    def _mark_all_recursive_inplace(self, value):
        """Recursively replace nested lists/dicts with 1s."""
        if isinstance(value, int):
            return 1
        if isinstance(value, list):
            return [ self._mark_all_recursive(v) for v in value ]
        if isinstance(value, dict):
            return { k: self._mark_all_recursive(v) for k, v in value.items() }
        raise TypeError(f"Unsupported value type in assignment: {type(value)}")
