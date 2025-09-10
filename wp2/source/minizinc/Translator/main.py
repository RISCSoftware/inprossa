from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
    code = """
a = [[1,1], [2, 4 +1], [3+1,5]]
a[1,2] = 5
"""
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)
