"""Contains tests for the unrolling translation module."""

import unittest
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

translation_tests = [
    {
        "name": "test_simple",
        "code": """
x = 0
""",
        "expected_translation": """array[1..1] of var int: x;
constraint x[1] = 0;
solve satisfy;"""
    },
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
VALUES = [1, 2]
x = 0
for t in VALUES:
    x = x + t
""",
        "expected_translation": """array[1..2] of int: VALUES = [1, 2];
array[1..3] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + VALUES[1]);
constraint x[3] = (x[2] + VALUES[2]);
solve satisfy;"""
    },
    {
        "name": "test_for_as_index_of_list",
        "code": """
VALUES = [1, 2, 4]
x = 0
for i in range(1, 4):
    x = x + VALUES[i]
""",
        "expected_translation": """array[1..3] of int: VALUES = [1, 2, 4];
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
VALUES = [1, 2, 4]
I = 3
x = 0
x = x + VALUES[I]
""",
        "expected_translation": """array[1..3] of int: VALUES = [1, 2, 4];
int: I = 3;
array[1..2] of var int: x;
constraint x[1] = 0;
constraint x[2] = (x[1] + VALUES[I]);
solve satisfy;"""
    },
    {
        "name": "test_variable_created_in_if",
        "code": """
I = 0
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
I = 0
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
I = 0
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
a: float
a = 0
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
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
array[1..1] of var int: c;
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
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
array[1..1] of var int: d__1;
array[1..1] of var int: c;
array[1..1] of var int: d;
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
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..1] of var int: c__1;
array[1..1] of var int: c;
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
array[1..1] of var int: a__1;
array[1..1] of var int: b__1;
array[1..2] of var int: c__1;
array[1..1] of var int: d__1;
array[1..1] of var int: a__2;
array[1..1] of var int: b__2;
array[1..2] of var int: c__2;
array[1..1] of var int: d__2;
array[1..4] of var int: x;
array[1..1] of var int: c;
array[1..1] of var int: d;
array[1..1] of var int: e;
array[1..1] of var int: g;
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
array[1..1] of var int: a__1;
array[1..2] of var int: a__1__1;
array[1..1] of var int: b__1;
array[1..2] of var int: c__1;
array[1..1] of var int: c;
constraint g(2, 2, c[1], a__1, a__1__1, b__1, c__1);
solve satisfy;"""
    },
    {
        "name": "test_assign_list",
        "code": """
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
        failed += 1
        print(f"Test {test['name']} failed:")
        print("Code:")
        print(test["code"])
        print("Expected:")
        print(test["expected_translation"])
        print("Got:")
        print(result)
print(f"Total failed tests: {failed}")

# if __name__ == "__main__":
#     unittest.main()
#     TestMiniZincTranslation().test_translations()
