import json

import boto3
import os

import constants


class AwsClient:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.temperature = 0.7
        self.set_region_id()

        # Read API key from a local file
        with open(".api_key", "r") as f:
            self.api_key = f.read().strip()

        if self.api_key is None:
            print("API key not readable.")
            return

        # Set the API key as an environment variable
        os.environ['AWS_BEARER_TOKEN_BEDROCK'] = f"{self.api_key}"

        # Create the Bedrock client
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region_name
        )

    def send_prompt_with_model_id(self, prompt: str, model_id: str, system_prompt: str = None, max_tokens = 70):
        if constants.DEBUG_MODE_ON: print(f"Swaping from {self.model_id} to {model_id}.")
        self.model_id = model_id
        self.set_region_id()
        return self.send_prompt(system_prompt=system_prompt, prompt=prompt, max_tokens=max_tokens)

    def send_prompt(self,
            system_prompt: str = None,
            prompt: str = None,
            max_tokens = 700) -> str:

        response = ""

        # Make the API call
        try:
            if constants.USE_INVOKE_MODEL:
                if "amazon" in self.model_id:
                    if system_prompt is None:
                        chunked_response = self.client.invoke_model(
                            modelId=self.model_id,
                            body=json.dumps({
                                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                                "inferenceConfig": {
                                    'maxTokens': max_tokens,
                                    'temperature': self.temperature
                                }
                            })
                        )
                    else:
                        chunked_response = self.client.invoke_model(
                            modelId=self.model_id,
                            body=json.dumps({
                                "system" : [{"text": system_prompt}],
                                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                                "inferenceConfig": {
                                    'maxTokens': max_tokens,
                                    'temperature': self.temperature}
                            })
                        )
                elif "anthropic" in self.model_id:
                    messages = []
                    messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
                    if system_prompt is not None:
                        chunked_response = self.client.invoke_model(
                            modelId=self.model_id,
                            accept="application/json",
                            contentType="application/json",
                            body=json.dumps({
                                "anthropic_version": "bedrock-2023-05-31",
                                "system": system_prompt,
                                "messages": messages,
                                "max_tokens": max_tokens,
                                "temperature": self.temperature
                            })
                        )
                    else:
                        chunked_response = self.client.invoke_model(
                            modelId=self.model_id,
                            accept="application/json",
                            contentType="application/json",
                            body=json.dumps({
                                "anthropic_version": "bedrock-2023-05-31",
                                "messages": messages,
                                "max_tokens": max_tokens,
                                "temperature": self.temperature
                            })
                        )
                elif "llama" in self.model_id:
                    # Embed the prompt in Llama 3's instruction format.
                    formatted_prompt = "<|begin_of_text|>"
                    if system_prompt is not None:
                        formatted_prompt = formatted_prompt + """
                        <|start_header_id|>system<|end_header_id|>
                        {system_prompt}
                        <|eot_id|>"""
                    formatted_prompt = formatted_prompt + f"""
                    <|start_header_id|>user<|end_header_id|>
                    {prompt}
                    <|eot_id|>
                    <|start_header_id|>assistant<|end_header_id|>
                    """

                    chunked_response = self.client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps({
                            "prompt": formatted_prompt,
                            "max_gen_len": 512,
                            "temperature": 0.5,
                        })
                    )
                else:
                    # gpt-oss, mistral-pixtral, qwen-coder
                    #if self.model_id == "eu.mistral.pixtral-large-2502-v1:0":
                    #    self.tracker.record_attempt()
                    messages = []
                    if system_prompt is not None:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    chunked_response = self.client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps({
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": self.temperature
                        })
                    )

                if chunked_response.get("body"):
                    response = ""
                    for event in chunked_response.get("body"):
                        response += event.decode()
                response = json.loads(response)
            else:
                if system_prompt is None:
                    response = self.client.converse(
                        modelId=self.model_id,
                        messages=[{"role": "user", "content": [{"text": prompt}]}],
                        inferenceConfig={
                            'maxTokens': max_tokens,
                            'temperature': self.temperature
                        }
                    )
                else:
                    response = self.client.converse(
                        modelId=self.model_id,
                        messages=[{"role": "user", "content": [{"text": prompt}]}],
                        system=[{"text": system_prompt}],
                        inferenceConfig={
                            'maxTokens': max_tokens,
                            'temperature': self.temperature
                        }
                    )
        except Exception as e:
            print(e)
            return ""


        # Print the response
        if constants.DEBUG_MODE_ON:
            match self.model_id:
                case "eu.amazon.nova-lite-v1:0" | "eu.amazon.nova-pro-v1:0":
                    print(f"input tokens: {response["usage"]["inputTokens"]}")
                    print(f"output tokens: {response["usage"]["outputTokens"]}")
                    print(f"total tokens: {response["usage"]["totalTokens"]}")
                case "eu.meta.llama3-2-3b-instruct-v1:0":
                    print(f"input tokens: {response["prompt_token_count"]}")
                    print(f"output tokens: {response["generation_token_count"]}")
                case "eu.anthropic.claude-3-5-sonnet-20240620-v1:0" | "eu.anthropic.claude-3-7-sonnet-20250219-v1:0":
                    print(f"input tokens: {response["usage"]["input_tokens"]}")
                    print(f"output tokens: {response["usage"]["output_tokens"]}")
                    print(f"total tokens: {response["usage"]["input_tokens"] + response["usage"]["output_tokens"]}")
                    if "cached_tokens" in response["usage"]:
                        print(f"    (cached creation tokens: {response["usage"]["cache_creation_input_tokens"]})")
                        print(f"    (cached read tokens: {response["usage"]["cache_read_input_tokens"]})")
                case "qwen.qwen3-coder-480b-a35b-v1:0" | "openai.gpt-oss-120b-1:0" | "openai.gpt-oss-20b-1:0" | "eu.mistral.pixtral-large-2502-v1:0" | "deepseek.v3-v1:0" | "eu.meta.llama3-2-3b-instruct-v1:0":
                    print(f"input tokens: {response["usage"]["prompt_tokens"]}")
                    print(f"output tokens: {response["usage"]["completion_tokens"]}")
                    print(f"total tokens: {response["usage"]["total_tokens"]}")
                    if "cached_tokens" in response["usage"]:
                        print(f"    (cached tokens: {response["usage"]["cached_tokens"]})")
            # print(f"complete response: {response}\n\n")
        match (self.model_id):
            case "eu.amazon.nova-lite-v1:0" | "eu.amazon.nova-pro-v1:0":
                return response['output']['message']['content'][0]['text']
            case "eu.meta.llama3-2-3b-instruct-v1:0":
                return response['generation']
            case "eu.anthropic.claude-3-5-sonnet-20240620-v1:0" | "eu.anthropic.claude-3-7-sonnet-20250219-v1:0":
                return response['content'][0]['text']
            case "openai.gpt-oss-20b-1:0" | \
                 "qwen.qwen3-coder-480b-a35b-v1:0" | \
                 "qwen.qwen3-coder-30b-a3b-v1:0" | \
                 "eu.anthropic.claude-3-5-sonnet-20240620-v1:0" | \
                 "eu.mistral.pixtral-large-2502-v1:0" | \
                 "deepseek.v3-v1:0" | \
                 "eu.meta.llama3-2-3b-instruct-v1:0" | \
                 "openai.gpt-oss-120b-1:0" | \
                 "openai.gpt-oss-20b-1:0" :
                return response['choices'][0]['message']['content']
            case _:
                return ""

    def set_region_id(self):
        match self.model_id:
            case "eu.amazon.nova-lite-v1:0":
                self.region_name = "eu-west-1"
            case "eu.amazon.nova-pro-v1:0":
                self.region_name = "eu-west-1"
            case "qwen.qwen3-coder-480b-a35b-v1:0":
                self.region_name = "eu-north-1"
            case "qwen.qwen3-coder-30b-a3b-v1:0":
                self.region_name = "eu-north-1"
            case "openai.gpt-oss-120b-1:0":
                self.region_name = "eu-west-1"
            case "openai.gpt-oss-20b-1:0":
                self.region_name = "eu-west-1"
            case "eu.anthropic.claude-3-5-sonnet-20240620-v1:0":
                self.region_name = "eu-west-1"
            case "eu.anthropic.claude-3-7-sonnet-20250219-v1:0":
                self.region_name = "eu-west-1"
            case "eu.mistral.pixtral-large-2502-v1:0":
                self.region_name = "eu-west-1"
            case "deepseek.v3-v1:0":
                self.region_name = "eu-north-1"
            case "eu.meta.llama3-2-3b-instruct-v1:0":
                self.region_name = "eu-west-1"