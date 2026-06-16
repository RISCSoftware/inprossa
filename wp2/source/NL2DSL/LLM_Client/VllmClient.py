import os

from openai import OpenAI


class VllmClient:
    def __init__(
            self,
            base_url: str = "http://localhost:8080/v1",
            api_key: str = "sk‑local",  # dummy if your server does not enforce a real key
            model_name: str = "my‑local‑model"):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.api_key = api_key or ""

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=api_key
        )

    def send_prompt(
            self,
            system_prompt: str = None,
            prompt: str = None,
            max_tokens: int = 250,
            temperature: float = 0.7,
            stream: bool = False
    ):
        if prompt is None or len(prompt) == 0:
            raise ValueError("(System) Prompt cannot be None.")

        messages = [{"role": "user", "content": prompt}]
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})

        """Send a chat‑completion request to a locally‑hosted OpenAI‑API‑compatible LLama LLM."""
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        if stream:
            for chunk in resp:
                # In streaming mode chunk.choices[0].delta.content may hold content
                delta = chunk.choices[0].delta
                if delta.get("content"):
                    return delta["content"]
                return None
        else:
            return resp.choices[0].message.content

'''
import openai
openai.api_base = "http://140.78.11.120:8000/v1" # 140.78.11.120 2001:628:2010:1199::c1:c1
openai.api_key = "YOUR_SECRET_API_KEY"

response = openai.ChatCompletion.create(
    model="my_model",
    messages=[
      {"role":"system","content":"You are helpful."},
      {"role":"user","content":"Hello from outside!"}
    ]
)
print(response.choices[0].message.content)
'''