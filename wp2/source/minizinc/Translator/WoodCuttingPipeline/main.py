from Translator.WoodCuttingPipeline.pipeline import code_pipeline
from Translator.WoodCuttingPipeline.reordering_machine import code_reordering_machine
from Translator.WoodCuttingPipeline.cutting_machine import code_cutting_machine
from Translator.WoodCuttingPipeline.filtering_machine import code_filtering_machine
from Translator.WoodCuttingPipeline.check_machine import code_check_machine
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Translator.Objects.MinizincRunner import MiniZincRunner
from Translator.WoodCuttingPipeline.objects import code_objects
from Translator.WoodCuttingPipeline.constants import code_constants
from Translator.WoodCuttingPipeline.given_objects import code_given_objects
from Translator.Objects.trial import run_mzn_and_detect_inconsistency, run_mus
full_code = (
    code_constants
    + code_objects
    + code_given_objects
    + code_pipeline
    # + code_reordering_machine
    + code_cutting_machine
    # + code_filtering_machine
    # + code_check_machine
)

translator = MiniZincTranslator(full_code)
model = translator.unroll_translation()
print("\n")
print(model)
print("\n")

# runner = MiniZincRunner()
# result = runner.run(model)
# print(result)

# Test run_mzn_and_detect_inconsistency
fzn_path = run_mzn_and_detect_inconsistency(model)
print(fzn_path)
# Test run_mus
mus_result = run_mus(model)
print(mus_result)