# DSL Specification

## Overview
The purpose of this DSL is to easily describe industrial machines.

This language can serve as an input to a translator that generates the constraints that are produced by this machine.

## Design principles

- Pythonic
- Collecting types and bounds

## Example

Small DSL example. Description of the example. Input --> output

## Types
- Can be given by strings: str, float, bool, or any other internally defined type
- Can also be descibed combining these:
    -  ```python
        DSInt(lower_bound:int, upper_bound:int, name:str)
        ```
        Translated to MiniZinc as `type name = lower_bound..upper_bound`
    - ```python
        DSFloat(lower_bound:float, upper_bound:float, name:str)
        ```
        Translated to MiniZinc as `type name = lower_bound..upper_bound`
    - ```python
        DSList(length:int, type_of_elements:type, name:str)
        ```
        Translated to MiniZinc as `type name = array[1..length] of type_of_elements`
    - ```python
        DSRecord(fields:dict[str, type], name:str)
        ```
        Translated to MiniZinc as
        ```minizinc
        type name = record(
            str1: type1,
            str2: type2,
            ...
            );
## Core concepts
### Constants (declaration)
Are always written in capital letters.  
Their type must be given
Example
```python
MIN_LEN : int = 6
```

Saved internally as `Constant(name="MIN_LEN", value=6, type_=int)`

Translated to MiniZinc as `int: MIN_LEN = 6;`

### Variables (Statement, declaration is a: int)
Cannot be written completely in capital letters.  
If type is not given int is assumed.  
When variables are updated, in the single value translation, another version of the variable will be created.  
Example
```python
a = 5
a = a + 4
```
Will be stored internally as
```python
Variable(name='a', versions=2)
Constraint("a[1] = 5")
Constraint("a[2] = (a[1] + 4)")
```

Will be translated as
```minizinc
array[1..2] of int: a;
constraint a[1] = 5;
constraint a[2] = (a[1] + 4);
```

### Constraints (Statements)
To add extra constraints that are not indicated by equalities, assert can be used
Example:
```python
assert a > 3
```
Stored internally as

```python
Constraint("a[1] > 3")
```
Translated as
```
array[1..1] of int: a;
constraint (a[1] > 3);
```

### If (statement)
To handle ifs in our translation, we add the precondition to all constraints generated inside the if statement. Plus, in the branches in which the value doesn't change, we force values to equal those at the beginning

Example
```python
if a > 3:
    a = a + 1
```
Stored internally as

```python
Constraint("a[2] = a[1] + 1", conditions=["a > 3"])
Constraint("a[2] = a[1]", conditions=["not(a > 3)"])
```
Translated as
```
array[1..2] of int: a;
constraint (a[1] > 3) -> a[2] = (a[1] + 1);
constraint (not (a[1] > 3)) -> a[2] = a[1];
```

Else branches are also possible, and they can be nested as many times as desired.

### For (Statement)
When reaching a for (or enumerate) we simply translate each of the runs of the loop

Example:
```python
for i in range(3):
    a = a + 1
```
Stored internally as

```python
Constraint("a[2] = a[1] + 1")
Constraint("a[3] = a[2] + 1")
```
Translated as
```
array[1..3] of int: a;
constraint a[2] = (a[1] + 1);
constraint a[3] = (a[2] + 1);
```

### Functions -> Predicates (declarations)
Functions in the DSL turn into predicates in MiniZinc.  
Both inputs and outputs of the function become inputs of the predicates.  
As variables cannot be defined inside a predicate, any variables needed inside the predicate are given as an input.

```python
def my_fun(a: int, b: int) -> int:
    c = a + b
    d = c * 2
    return d
```

is stored internally 
```python
Predicate()
#with
.name = "my_fun"
.input_names = ["a", "b"]
.return_names = ["d"]
.constraints = [Constraint("c[1] = a[1] + b[1]"),
                Constraint("d[1] = 2 * c[1]")]
```
and its definition is translated to MiniZinc as
```minizinc
predicate my_fun(var int: input_1, var int: input_2, var int: output_1, array[1..1] of int: a, array[1..1] of int: b, array[1..1] of int: c, array[1..1] of int: d) =
    (
    a[1] = input_1 /\
    b[1] = input_2 /\
    c[1] = (a[1] + b[1]) /\
    d[1] = (c[1] * 2) /\
    output_1 = d[1]
    );
```

Every time a predicate (function) is called, new variables have to be defined.  
The names used are "name" + "__" + number of calls to this function so far, for example:
```minizinc
array[1..1] of int: a__1;
array[1..1] of int: b__1;
array[1..1] of int: c__1;
array[1..1] of int: d__1;
array[1..1] of int: a__2;
array[1..1] of int: b__2;
array[1..1] of int: c__2;
array[1..1] of int: d__2;
array[1..1] of int: d;
array[1..1] of int: e;
constraint my_fun(3, 4, d[1], a__1, b__1, c__1, d__1);
constraint my_fun(5, 6, e[1], a__2, b__2, c__2, d__2);
solve satisfy;
```