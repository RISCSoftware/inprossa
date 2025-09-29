from Translator.Objects.Declaration import Declaration

def test_scalar_decision_int():
    x = Declaration("x")
    assert x.to_minizinc() == "var int: x"


def test_bounded_scalar_decision_int():
    y = Declaration("y", lower=0, upper=1)
    assert y.to_minizinc() == "var 0..1: y"


def test_1d_array_length_7():
    a = Declaration("a", dims=7)
    assert a.to_minizinc() == "array[1..7] of var int: a"


def test_2d_array_int_sizes():
    mat = Declaration("mat", dims=(3, 4))
    assert mat.to_minizinc() == "array[1..3, 1..4] of var int: mat"


def test_2d_array_symbolic_sizes():
    tab = Declaration("tab", dims=("N", "M"))
    assert tab.to_minizinc() == "array[1..N, 1..M] of var int: tab"


def test_float_vector_with_bounds_and_symbolic_len():
    w = Declaration("w", type_="float", lower=0.0, upper=1.0, dims="K")
    assert w.to_minizinc() == "array[1..K] of var 0.0..1.0: w"


if __name__ == "__main__":
    test_scalar_decision_int()
    test_bounded_scalar_decision_int()
    test_1d_array_length_7()
    test_2d_array_int_sizes()
    test_2d_array_symbolic_sizes()
    test_float_vector_with_bounds_and_symbolic_len()
    print("All tests passed.")