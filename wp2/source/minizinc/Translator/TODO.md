An object will always be one of 4 kinds
1. int/float/bool
2. List (all the same kind)
3. NamedTuple
To define the first type I will use:
    1.1. int/float/bool
    1.2. Annotated to define the limits: 
         e.g. Annotated("lb=1, ub=5") -> int
         e.g. Annotated("lb=2.2, ub=6.5") -> float
    1.3. Annotated to define the limits with type (must check that makes sense and convert accordingly): 
         e.g. Annotated(int, "lb=1.4, ub=5.3") -> 2..5 (in MiniZinc)
         e.g. Annotated(float, "lb=2, ub=6") -> 2.0..6.0 (in MiniZinc)
    1.4. Another option is to use DSBoundType(1.4, 5.3)
To define a list we will use:
    2.1 MyListType = DSList(MyType, length) -> type MyListType = array[1..length] of MyType (in MiniZinc)
To define a named tuple, we will use:
    3.1 class MyNamedTuple(name1: TypeOfName1, name2: TypeOfName2) -> record in MiniZinc

To give the type of a variable we use
x: MyType
if no type is specified "int" is assumed

To save the types after reading them, maybe it's best as diccionaries

When a variable is updated, we add one to the counter of versions and create an assertion to impose the new value

When a part of a list or a named tuple is updated, we add one to the version counter, in the new version assert all not modified parts to be the same as in the prev version and the modified part is asserted to be equal to the specified value


