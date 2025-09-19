from pipeline import code_pipeline
from reordering_machine import code_reordering_machine
from cutting_machine import code_cutting_machine
from filtering_machine import code_filtering_machine
from check_machine import code_check_machine
from Translator.Objects.MiniZincTranslator import MiniZincTranslator

full_code = code_pipeline + code_reordering_machine + code_cutting_machine + code_filtering_machine + code_check_machine
MiniZincTranslator(full_code).unroll_translation()