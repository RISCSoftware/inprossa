
from LLM_Client.AwsClient import AwsClient

USE_OPTDSL = True
USE_TYPING = False
USE_PYDANTIC = True
#CHOSEN_LANGUAGE = "z3py"
CHOSEN_LANGUAGE = "optdsl"
DEBUG_MODE_ON = True
SYSTEM_PROMPT_FOLDER = ("prompts/optdsl_typing/" if USE_OPTDSL else "prompts/z3py_typing/") \
    if USE_TYPING else \
    (("prompts/optdsl_pydantic/" if USE_OPTDSL else "prompts/z3py_pydantic/")
     if USE_PYDANTIC
     else ("prompts/optdsl/" if USE_OPTDSL else "prompts/z3py/"))

USE_INVOKE_MODEL = True
USE_ALL_AT_ONCE_AND_EXTRACT = False


'''
LLM = LocalLlamaClient(
    base_url="http://localhost:8080",
    api_key="local",
    model_name="Qwen2.5-Coder-7B-Q8_0-GGUF"
)
LLM = LocalLlamaClient(
    base_url="http://localhost:8081",
    api_key="local",
    model_name="Qwen3-4B-GGUF"
)
LLM = LocalLlamaClient(
    base_url="http://localhost:8080",
    api_key="local",
    model_name="Qwen3-4B-Instruct-2507-Q8_0-GGUF"
)'''
# LLM = AwsClient(model_id="eu.amazon.nova-lite-v1:0")
# LLM = AwsClient(model_id="eu.amazon.nova-pro-v1:0")                       # does well syntax-wise for all-at-once-approach only
# LLM = AwsClient(model_id="openai.gpt-oss-20b-1:0")                        # does well syntax-wise for all-at-once-approach only (always ads reasoning)
# LLM = AwsClient(model_id="openai.gpt-oss-120b-1:0")                       # does well syntax-wise for all-at-once-approach only (always ads reasoning)
LLM = AwsClient(model_id="qwen.qwen3-coder-480b-a35b-v1:0")                 # does well syntax-wise for iterative build-up and all-at-once, timeout
# LLM = AwsClient(model_id="qwen.qwen3-coder-30b-a3b-v1:0")
# LLM = AwsClient(model_id="deepseek.v3-v1:0")                              # does well syntax-wise for all-at-once-approach only
# LLM = AwsClient(model_id="eu.anthropic.claude-3-5-sonnet-20240620-v1:0")  # Model use case details have not been submitted for this account.
# LLM = AwsClient(model_id="eu.anthropic.claude-3-7-sonnet-20250219-v1:0")  # Model use case details have not been submitted for this account.
# LLM = AwsClient(model_id="eu.mistral.pixtral-large-2502-v1:0")            # does well syntax-wise for all-at-once-approach only, ThrottlingException (reached max retries: 4)

# LLM = AwsClient(model_id="eu.meta.llama3-2-3b-instruct-v1:0") # yields terrible results, never adheres to format specifications

'''
LLM = VllmClient(
    base_url="http://140.78.11.121:9000/v1",
    api_key="EMPTY",
    model_name="Qwen/Qwen3-4B-Instruct-2507"
)
'''

