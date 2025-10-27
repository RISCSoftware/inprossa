"""Contains tests for the unrolling translation module."""

import unittest
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

translation_tests = [
    {
        "name": "dsint_positional",
        "code": """
MyInt = DSInt(3, 7)
""",
        "expected_translation": """type MyInt = 3..7;
solve satisfy;"""
    },
    {
        "name": "dsint_keyword_names",
        "code": """
MAX_N : int = 10
LB : int = 0
UB : int = MAX_N
MyInt2 = DSInt(lb=LB, ub=UB)
""",
        "expected_translation": """type MyInt2 = LB..UB;
int: MAX_N = 10;
int: LB = 0;
int: UB = 10;
solve satisfy;"""
    },
    {
        "name": "dsfloat_unit_interval",
        "code": """
MyFloat = DSFloat(lb=0.0, ub=1.0)
""",
        "expected_translation": """type MyFloat = 0.0..1.0;
solve satisfy;"""
    },
    {
        "name": "dsfloat_unit_interval",
        "code": """
MyFloatList = DSList(5, elem_type=DSFloat(lb=0.0, ub=1.0))
""",
        "expected_translation": """type MyFloatList = array[1..5] of 0.0..1.0;
solve satisfy;"""
    },
    {
        "name": "dsbool_simple",
        "code": """
Flag = DSBool()
""",
        "expected_translation": """type Flag = bool;
solve satisfy;"""
    },
    {
        "name": "dslist_constant",
        "code": """
VEC : DSList(5) = [1, 2, 3, 4, 5]
""",
        "expected_translation": """array[1..5] of int: VEC = [1, 2, 3, 4, 5];
solve satisfy;"""
    },
    {
        "name": "dslist_default_elem_int",
        "code": """
Vec = DSList(5)
""",
        "expected_translation": """type Vec = array[1..5] of int;
solve satisfy;"""
    },
    # Use keyword for elem_type to match your current DSList (elem_type kept as ast.Name)
    {
        "name": "dslist_keyword_elem_builtin",
        "code": """
Vec2 = DSList(length=4, elem_type=int)
""",
        "expected_translation": """type Vec2 = array[1..4] of int;
solve satisfy;"""
    },
    {
        "name": "dslist_keyword_elem_custom",
        "code": """
MyInt = DSInt(3, 7)
Vec3 = DSList(length=10, elem_type=MyInt)
""",
        "expected_translation": """type MyInt = 3..7;
type Vec3 = array[1..10] of MyInt;
solve satisfy;"""
    },
    # DSRecord per your current emitter: multi-line record(...) with "type: name" fields
    {
        "name": "dsrecord_simple",
        "code": """
Person = DSRecord({"name": "float", "age": "int"})
""",
        "expected_translation": """type Person = record(
    float: name,
    int: age
);
solve satisfy;"""
    },
]
translation_tests += [
    {
        "name": "record_with_custom_and_list",
        "code": """
MyInt = DSInt(3, 7)
VecMyInt5 = DSList(length=5, elem_type=MyInt)
Person = DSRecord({"name": "float", "scores": "VecMyInt5", "grade": "MyInt"})
""",
        "expected_translation": """type MyInt = 3..7;
type VecMyInt5 = array[1..5] of MyInt;
type Person = record(
    float: name,
    VecMyInt5: scores,
    MyInt: grade
);
solve satisfy;"""
    },
    {
        "name": "record_with_float_and_list",
        "code": """
Prob = DSFloat(lb=0.0, ub=1.0)
Vec10 = DSList(length=10, elem_type=int)
Sample = DSRecord({"id": "int", "values": "Vec10", "prob": "Prob"})
""",
        "expected_translation": """type Prob = 0.0..1.0;
type Vec10 = array[1..10] of int;
type Sample = record(
    int: id,
    Vec10: values,
    Prob: prob
);
solve satisfy;"""
    },
    {
        "name": "record_of_records_and_list",
        "code": """
Point = DSRecord({"x": "int", "y": "int"})
Points = DSList(length=3, elem_type=Point)
Polygon = DSRecord({"name": "float", "points": "Points"})
""",
        "expected_translation": """type Point = record(
    int: x,
    int: y
);
type Points = array[1..3] of Point;
type Polygon = record(
    float: name,
    Points: points
);
solve satisfy;"""
    },
    {
        "name": "nested_records_with_custom_zip_and_group",
        "code": """
Zip = DSInt(10000, 99999)
Address = DSRecord({"street": "float", "zip": "Zip"})
User = DSRecord({"name": "float", "addr": "Address"})
Group = DSList(length=2, elem_type=User)
Team = DSRecord({"members": "Group"})
""",
        "expected_translation": """type Zip = 10000..99999;
type Address = record(
    float: street,
    Zip: zip
);
type User = record(
    float: name,
    Address: addr
);
type Group = array[1..2] of User;
type Team = record(
    Group: members
);
solve satisfy;"""
    },
]

translation_tests += [
    {
        "name": "test_simple",
        "code": """
x = 0
""",
        "expected_translation": """array[1..1] of var int: x;
constraint x[1] = 0;
solve satisfy;"""
    },
#     {
#         "name": "test_simple_subscript",
#         "code": """
# x[1] = 0
# """,
#         "expected_translation": """array[1..1] of var array[1..1] of var int: x;
# constraint x[1][1] = 0;
# solve satisfy;"""
#     },
    {
        "name": "test_simple_assert",
        "code": """
assert x > 0
""",
        "expected_translation": """array[1..1] of var int: x;
constraint (x[1] > 0);
solve satisfy;"""
    },
    {
        "name": "test_simple_if",
        "code": """
x = 0
if x > 0:
    x = x + 1
""",
        "expected_translation": """array[1..2] of var int: x;
constraint x[1] = 0;
constraint (x[1] > 0) -> x[2] = (x[1] + 1);
constraint (not (x[1] > 0)) -> x[2] = x[1];
solve satisfy;"""
    },
    {
        "name": "test_if_else",
        "code": """
x = 0
if x > 0:
    x = x + 1
else:
    x = x - 1
""",
        "expected_translation": """array[1..2] of var int: x;
constraint x[1] = 0;
constraint (x[1] > 0) -> x[2] = (x[1] + 1);
constraint (not (x[1] > 0)) -> x[2] = (x[1] - 1);
solve satisfy;"""
    },
    {
    "name": "test_nested_ifs",
    "code": """
x = 0
y = 0
if x > 0:
    if y < 5:
        y = y + 1
""",
    "expected_translation": """array[1..1] of var int: x;
array[1..2] of var int: y;
constraint x[1] = 0;
constraint y[1] = 0;
constraint (y[1] < 5) /\\ (x[1] > 0) -> y[2] = (y[1] + 1);
constraint (not (y[1] < 5)) /\\ (x[1] > 0) -> y[2] = y[1];
constraint (not (x[1] > 0)) -> y[2] = y[1];
solve satisfy;"""
},
{
    "name": "test_simple_for_range",
    "code": """
x = 0
for i in range(1, 3):
    x = x + i
""",
    "expected_translation": """array[1..3] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + 1);
constraint x[3] = (x[2] + 2);
solve satisfy;"""
},
{
    "name": "test_nested_for",
    "code": """
x = 0
for i in range(1, 3):
    for j in range(1, 3):
        x = x + j
""",
    "expected_translation": """array[1..5] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + 1);
constraint x[3] = (x[2] + 2);
constraint x[4] = (x[3] + 1);
constraint x[5] = (x[4] + 2);
solve satisfy;"""
},
{
    "name": "test_if_inside_for",
    "code": """
x = 0
for i in range(1, 3):
    if i == 1:
        x = x + 1
""",
    "expected_translation": """array[1..3] of var int: x;
constraint x[1] = 0;
constraint (1 = 1) -> x[2] = (x[1] + 1);
constraint (not (1 = 1)) -> x[2] = x[1];
constraint (2 = 1) -> x[3] = (x[2] + 1);
constraint (not (2 = 1)) -> x[3] = x[2];
solve satisfy;"""
},
{
    "name": "test_for_inside_if",
    "code": """
x = 0
if x == 0:
    for i in range(1, 3):
        x = x + i
""",
    "expected_translation": """array[1..3] of var int: x;
constraint x[1] = 0;
constraint (x[1] = 0) -> x[2] = (x[1] + 1);
constraint (x[1] = 0) -> x[3] = (x[2] + 2);
constraint (not (x[1] = 0)) -> x[3] = x[1];
solve satisfy;"""
}
]
translation_tests += [
    {
        "name": "test_for_with_range_constants",
        "code": """
x = 0
for i in range(1, 4):
    x = x + i
""",
        "expected_translation": """array[1..4] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + 1);
constraint x[3] = (x[2] + 2);
constraint x[4] = (x[3] + 3);
solve satisfy;"""
    },
    {
        "name": "test_for_with_list_literal",
        "code": """
x = 0
for t in [3, 1, 5]:
    x = x + t
""",
        "expected_translation": """array[1..4] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + 3);
constraint x[3] = (x[2] + 1);
constraint x[4] = (x[3] + 5);
solve satisfy;"""
    },
    {
        "name": "test_for_with_enumerate_list",
        "code": """
x = 0
for i, t in enumerate([4, 2]):
    x = x + t + i
""",
        "expected_translation": """array[1..3] of var int: x;
constraint x[1] = 0;
constraint x[2] = ((x[1] + 4) + 1);
constraint x[3] = ((x[2] + 2) + 2);
solve satisfy;"""
    },
    {
        "name": "test_for_with_constant_list",
        "code": """
ValueType = DSList(2, int)
VALUES: ValueType = [1, 2];
x = 0
for t in VALUES:
    x = x + t
""",
        "expected_translation": """type ValueType = array[1..2] of int;
ValueType: VALUES = [1, 2];
array[1..3] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + VALUES[1]);
constraint x[3] = (x[2] + VALUES[2]);
solve satisfy;"""
    },
    {
        "name": "test_for_as_index_of_list",
        "code": """
ValueType = DSList(3, int)
VALUES : ValueType = [1, 2, 4]
x = 0
for i in range(1, 4):
    x = x + VALUES[i]
""",
        "expected_translation": """type ValueType = array[1..3] of int;
ValueType: VALUES = [1, 2, 4];
array[1..4] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + VALUES[1]);
constraint x[3] = (x[2] + VALUES[2]);
constraint x[4] = (x[3] + VALUES[3]);
solve satisfy;"""
    },
    {
        "name": "test_constant_as_index_of_list",
        "code": """
MyList = DSList(3, int)
VALUES : MyList = [1, 2, 4]
I : int = 3
x = 0
x = x + VALUES[I]
""",
        "expected_translation": """type MyList = array[1..3] of int;
MyList: VALUES = [1, 2, 4];
int: I = 3;
array[1..2] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + VALUES[I]);
solve satisfy;"""
    },
    {
        "name": "test_variable_created_in_if",
        "code": """
I : int = 0
if I == 0:
    x = 1
""",
        "expected_translation": """int: I = 0;
array[1..1] of var int: x;
constraint (I = 0) -> x[1] = 1;
solve satisfy;"""
    },
    {
        "name": "test_absolute_value",
        "code": """
I : int = 0
assert abs(x - I) == 1
""",
        "expected_translation": """int: I = 0;
array[1..1] of var int: x;
constraint (abs((x[1] - I)) = 1);
solve satisfy;"""
    },
    {
        "name": "test_not_declared_variable",
        "code": """
I : int = 0
assert x > I
""",
        "expected_translation": """int: I = 0;
array[1..1] of var int: x;
constraint (x[1] > I);
solve satisfy;"""
    },
    {
        "name": "test_float_type",
        "code": """
a : float
a = 0
""",
        "expected_translation": """array[1..1] of var float: a;
constraint a[1] = 0;
solve satisfy;"""
    },
    {
        "name": "test_float_type2",
        "code": """
a : float = 0
""",
        "expected_translation": """array[1..1] of var float: a;
constraint a[1] = 0;
solve satisfy;"""
    },
    {
        "name": "test_simple_function",
        "code": """
def f(a, b):
    c = a + b
    return c
c = f(1, 2)
""",
        "expected_translation": """predicate f(var int: input_1, var int: input_2, var int: output_1, array[1..1] of var int: a, array[1..1] of var int: b, array[1..1] of var int: c) =
    (
    a[1] = input_1 /\\
    b[1] = input_2 /\\
    c[1] = (a[1] + b[1]) /\\
    output_1 = c[1]
    );
array[1..1] of var int: c;
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
constraint f(1, 2, c[1], a__1, b__1, c__1);
solve satisfy;"""
    },
    {
        "name": "test_two_output_function",
        "code": """
def f(a, b):
    c = a + b
    d = a * b
    return c, d
c, d = f(1, 2)
""",
        "expected_translation": """predicate f(var int: input_1, var int: input_2, var int: output_1, var int: output_2, array[1..1] of var int: a, array[1..1] of var int: b, array[1..1] of var int: c, array[1..1] of var int: d) =
    (
    a[1] = input_1 /\\
    b[1] = input_2 /\\
    c[1] = (a[1] + b[1]) /\\
    d[1] = (a[1] * b[1]) /\\
    output_1 = c[1] /\\
    output_2 = d[1]
    );
array[1..1] of var int: c;
array[1..1] of var int: d;
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
array[1..1] of var int: d__1;
constraint f(1, 2, c[1], d[1], a__1, b__1, c__1, d__1);
solve satisfy;"""
    },
    {
        "name": "test_simple_predicate",
        "code": """
def f(a, b):
    c = a + b
    return c

c = f(1, 2)
""",
        "expected_translation": """predicate f(var int: input_1, var int: input_2, var int: output_1, array[1..1] of var int: a, array[1..1] of var int: b, array[1..1] of var int: c) =
    (
    a[1] = input_1 /\\
    b[1] = input_2 /\\
    c[1] = (a[1] + b[1]) /\\
    output_1 = c[1]
    );
array[1..1] of var int: c;
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
constraint f(1, 2, c[1], a__1, b__1, c__1);
solve satisfy;"""
    },
    {
        "name": "test_predicate",
        "code": """
def f(a, b):
    c = a + b
    d = a * b
    c = c * d
    return c, d

x = 0
for t in [3, 1, 5]:
    x = x + t

c, d = f(x, 2)
e, g = f(c, d)
assert c > d
""",
        "expected_translation": """predicate f(var int: input_1, var int: input_2, var int: output_1, var int: output_2, array[1..1] of var int: a, array[1..1] of var int: b, array[1..2] of var int: c, array[1..1] of var int: d) =
    (
    a[1] = input_1 /\\
    b[1] = input_2 /\\
    c[1] = (a[1] + b[1]) /\\
    d[1] = (a[1] * b[1]) /\\
    c[2] = (c[1] * d[1]) /\\
    output_1 = c[2] /\\
    output_2 = d[1]
    );
array[1..4] of var int: x;
array[1..1] of var int: c;
array[1..1] of var int: d;
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..2] of var int: c__1;
array[1..1] of var int: d__1;
array[1..1] of var int: e;
array[1..1] of var int: g;
array[1..1] of var int: a__2;
array[1..1] of var int: b__2;
array[1..2] of var int: c__2;
array[1..1] of var int: d__2;
constraint x[1] = 0;
constraint x[2] = (x[1] + 3);
constraint x[3] = (x[2] + 1);
constraint x[4] = (x[3] + 5);
constraint f(x[4], 2, c[1], d[1], a__1, b__1, c__1, d__1);
constraint f(c[1], d[1], e[1], g[1], a__2, b__2, c__2, d__2);
constraint (c[1] > d[1]);
solve satisfy;"""
    },
    {
        "name": "test_nested_function",
        "code": """
def f(a):
    if a > 0:
        a = 1
    else:
        a = 0
    return a

def g(a, b):
    c = f(a)
    c = c + b
    return c

c = g(2, 2)
""",
        "expected_translation": """predicate f(var int: input_1, var int: output_1, array[1..2] of var int: a) =
    (
    a[1] = input_1 /\\
    ((a[1] > 0) -> a[2] = 1) /\\
    ((not (a[1] > 0)) -> a[2] = 0) /\\
    output_1 = a[2]
    );
predicate g(var int: input_1, var int: input_2, var int: output_1, array[1..1] of var int: a, array[1..2] of var int: a__1, array[1..1] of var int: b, array[1..2] of var int: c) =
    (
    a[1] = input_1 /\\
    b[1] = input_2 /\\
    f(a[1], c[1], a__1) /\\
    c[2] = (c[1] + b[1]) /\\
    output_1 = c[2]
    );
array[1..1] of var int: c;
array[1..1] of var int: a__1;
array[1..2] of var int: a__1__1;
array[1..1] of var int: b__1;
array[1..2] of var int: c__1;
constraint g(2, 2, c[1], a__1, a__1__1, b__1, c__1);
solve satisfy;"""
    },
    {
        "name": "test_assign_list",
        "code": """
pieces : DSList(2, DSList(3, int))
pieces = [[2,1,5],[2,12,53]]
pieces[1] = pieces[1]
""",
        "expected_translation": """array[1..2] of array[1..2] of array[1..3] of var int: pieces;
constraint pieces[1][1][1] = [[2, 1, 5], [2, 12, 53]][1][1];
constraint pieces[1][1][2] = [[2, 1, 5], [2, 12, 53]][1][2];
constraint pieces[1][1][3] = [[2, 1, 5], [2, 12, 53]][1][3];
constraint pieces[1][2][1] = [[2, 1, 5], [2, 12, 53]][2][1];
constraint pieces[1][2][2] = [[2, 1, 5], [2, 12, 53]][2][2];
constraint pieces[1][2][3] = [[2, 1, 5], [2, 12, 53]][2][3];
constraint pieces[2][1] = pieces[1][1];
solve satisfy;"""
    },
]


class TestMiniZincTranslation(unittest.TestCase):

    def test_translations(self):
        for test in translation_tests:
            with self.subTest(test["name"]):
                translator = MiniZincTranslator(test["code"])
                result = translator.unroll_translation().strip()
                expected = test["expected_translation"].strip()
                self.assertEqual(result, expected)
                if result != expected:
                    print("Unexpected translation result:")
                    print("Got:")
                    print(result)
                    print("Expected:")
                    print(expected)

failed = 0
for test in translation_tests:
    print(f"Test {test['name']}")
    translator = MiniZincTranslator(test["code"])
    result = translator.unroll_translation()
    if result != test["expected_translation"]:
        print(f"Test {test['name']} failed:")
        print("Code:")
        print(test["code"])
        print("Expected:")
        print(test["expected_translation"])
        print("Got:")
        print(result)
        failed += 1
print(f"Total failed tests: {failed}")

# if __name__ == "__main__":
#     unittest.main()
#     TestMiniZincTranslation().test_translations()
