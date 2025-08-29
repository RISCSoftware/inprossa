from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
    code = """
if a > 0:
    b = 1
else:
    c = 0
if a > 1:
    b = 2
else:
    b = 0
"""
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)
