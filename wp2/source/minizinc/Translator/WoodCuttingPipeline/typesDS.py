from typing import Optional, Union, Dict
from dataclasses import dataclass

class DSInt:
    def __init__(self,
                 lb: Optional[int] = None,
                 ub: Optional[int] = None):
        self.lb = lb
        self.ub = ub

class DSFloat:
    def __init__(self,
                 lb: Optional[float] = None,
                 ub: Optional[float] = None):
        self.lb = lb
        self.ub = ub

class DSBool:
    pass

class DSList:
    def __init__(self,
                 length: Union[int, str],
                 elem_type: type
                 ):
        self.length = length
        self.elem_type = elem_type

class DSRecord:
    def __init__(self,
                 name: str,
                 fields: Dict[str, type]):
        self.name = name
        self.fields = fields
