
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
RANDOM_SEED = 20
RANDOM_STRING_LENGTH = 10

# DFS Tree of Thought
NR_MAX_CHILDREN = 4
CONSTRAINT_NODES = False
SAVE_NODES = False
SAVE_MODEL = True
SOLVER = "chuffed"

# AlgoPolish
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
        LLM = AwsClient(model_id="qwen.qwen3-coder-480b-a35b-v1:0")                 # does well syntax-wise for iterative build-up and all-at-once, timeout

    return LLM
