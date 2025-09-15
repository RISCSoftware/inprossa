from Translator.Objects.MiniZincTranslator import MiniZincTranslator



# ===== Example usage =====
if __name__ == "__main__":
    code = """
pieces = [[2,1,5],[2,12,53]]
pieces[1] = pieces[1]
"""
    translator = MiniZincTranslator(code)
    model = translator.unroll_translation()
    print(model)
