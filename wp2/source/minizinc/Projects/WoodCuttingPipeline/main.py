from Projects.WoodCuttingPipeline.pipeline import code_pipeline
from Projects.WoodCuttingPipeline.reordering_machine import code_reordering_machine
from Projects.WoodCuttingPipeline.cutting_machine import code_cutting_machine
from Projects.WoodCuttingPipeline.filtering_machine import code_filtering_machine
from Projects.WoodCuttingPipeline.check_machine import code_check_machine
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from Tools.MinizincRunner import MiniZincRunner
from Projects.WoodCuttingPipeline.objects import code_objects
from Projects.WoodCuttingPipeline.constants import code_constants
from Projects.WoodCuttingPipeline.given_objects import code_given_objects
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


if __name__ == "__main__":
    translator = MiniZincTranslator(full_code)
    model = translator.unroll_translation()
    print("\n")
    print(model)
    print("\n")

    runner = MiniZincRunner()
    result = runner.run(model)
    print(result)