from pipeline import code_pipeline
from reordering_machine import code_reordering_machine
from cutting_machine import code_cutting_machine
from filtering_machine import code_filtering_machine
from check_machine import code_check_machine
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from objects import code_objects
from constants import code_constants
from given_objects import code_given_objects
full_code = code_constants + code_objects + code_given_objects + code_pipeline + code_reordering_machine + code_cutting_machine + code_filtering_machine + code_check_machine

translator = MiniZincTranslator(full_code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")
