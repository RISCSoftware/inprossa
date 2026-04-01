
from LLM_Client.AwsClient import AwsClient

# ***************** NON-CUSTOMIZABLE SETTINGS ******************
# Please leave these settings unchanged
USE_OPTDSL = True
USE_TYPING = False
USE_PYDANTIC = True
#CHOSEN_LANGUAGE = "z3py"
CHOSEN_LANGUAGE = "optdsl"
SYSTEM_PROMPT_FOLDER = ("prompts/optdsl_typing/" if USE_OPTDSL else "prompts/z3py_typing/") \
    if USE_TYPING else \
    (("prompts/optdsl_pydantic_minmaximize/" if USE_OPTDSL else "prompts/z3py_pydantic/") #
     if USE_PYDANTIC
     else ("prompts/optdsl/" if USE_OPTDSL else "prompts/z3py/"))

USE_INVOKE_MODEL = True
USE_ALL_AT_ONCE_AND_EXTRACT = False

LLM = None

# **************** CUSTOMIZABLE SETTINGS ******************

DEBUG_MODE_ON = True
SOLVE_TIME_TIMEOUT = 150000
RANDOM_SEED = 20
RANDOM_STRING_LENGTH = 10

# DFS Tree of Thought
NR_MAX_CHILDREN = 4 # Maximum of children per node in ToT
CONSTRAINT_NODES = False # default: false. Splits each subproblem into individual node, save formulations for all subproblems into one node
SAVE_NODES = False # Saves whole tree: each node in correct nested folder structure
SAVE_MODEL = True # Saves the valid model formulations resulting from the tree
SOLVER = "chuffed"

# AlgoPolish
ALGOPOLISH_TESTSET_PATH = "problem_descriptions/testset_algopolish_2D-BPP_CLASS_XS"
CODE_LENGTH_PENALTY = 0.25

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
