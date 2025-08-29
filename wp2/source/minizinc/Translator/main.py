from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
#     code = """
# def f(a, b):
#     c = a + b
#     d = a * b
#     c = c * d
#     return c, d

# x = 0
# for t in [3, 1, 5]:
#     x = x + t

# c, d = f(x, 2)
# e, g = f(c, d)
# assert c > d
# """
    code = """
def f(a, b):
    c = a + b
    d = a * b
    return c
a = 0
a: float
a: int = 2
c = f(a, 2)
"""

# code = """
# def cutting(length, cut1, cut2):
#     len1 = cut1
#     len2 = cut2 - cut1
#     len3 = length - cut2
#     return len1, len2, len3

# len1, len2, len3 = cutting(10, 2, 5)
# """
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)
