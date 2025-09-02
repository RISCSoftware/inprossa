from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
    code = """
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
"""
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)
