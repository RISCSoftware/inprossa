import BinPackingValidator
from LLM_Client.AwsClient import AwsClient

# ***************** NON-CUSTOMIZABLE SETTINGS ******************
# Please leave these settings unchanged
# DFS Tree of Thought
USE_OPTDSL = True
USE_TYPING = False
USE_PYDANTIC = True
CHOSEN_LANGUAGE = "optdsl"
SYSTEM_PROMPT_FOLDER = "prompts/optdsl_pydantic_minmaximize/"

USE_INVOKE_MODEL = True
USE_ALL_AT_ONCE_AND_EXTRACT = False

LLM = None

# AlgoPolish
ALGOPOLISH_TESTSET_PATH = "problem_descriptions/testset_algopolish_2D-BPP_CLASS" # Path to test set for evaluating AlgoPolish-heuristic
VALIDATE_SOLUTION = BinPackingValidator.validate_solution                        # Validator function
OBJECTIVE_VARIABLE_NAME = "nr_used_boxes"                                        # Decision variable representing the objective


# **************** CUSTOMIZABLE SETTINGS ******************

DEBUG_MODE_ON = True
SOLVE_TIME_TIMEOUT = 150000
RANDOM_SEED = 20
RANDOM_STRING_LENGTH = 10
ALGOPOLISH_ACTIVE = False

# DFS Tree of Thought
NR_MAX_CHILDREN = 2         # Maximum of children per node in ToT
CONSTRAINT_NODES = False    # default: false. Splits each subproblem into individual node, save formulations for all subproblems into one node
SAVE_NODES = False          # Saves whole tree: each node in correct nested folder structure
SAVE_MODEL = True           # Saves the valid model formulations resulting from the tree
SOLVER = "chuffed"          # MiniZinc backend solver
GENERATION_INST_DIR = "problem_descriptions/testset_paper_2D-BPP_CLASS/" # path to problem instances

# AlgoPolish
NR_MERGED_MODELS = 5        # Number of max. allowed formulations, resulting from merge, per iteration
POLISHING_ITERATIONS = 5    # Number of AlgoPlolish iterations (1 iteration = 5 formulations from merging + 3 formulations from refactoring)

# LLM Client
def get_LLM_client():
    global LLM
    if LLM is None:
        # LLM = VllmClient(
        #     base_url="http://localhost:8080",
        #     api_key="local",
        #     model_name="Qwen2.5-Coder-7B-Q8_0-GGUF"
        # )
        LLM = AwsClient(model_id="qwen.qwen3-coder-480b-a35b-v1:0")
    return LLM

