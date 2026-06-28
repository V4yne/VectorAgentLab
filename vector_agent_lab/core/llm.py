"""Unified LLM interface.

Planned responsibility:
- define a model-agnostic chat/completion protocol
- hide differences between OpenAI, Anthropic, Ollama, and test models
- make Agent logic independent from model vendors
"""

import os
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()  # Load .env file if it exists.


class VectorAgentsLLM:
    """Base LLM client for the default GPT/OpenAI-compatible provider."""

    provider = "gpt"

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize the default GPT/OpenAI-compatible LLM client.

        Prefer passed parameters. If parameters are not provided, read them
        from LLM_MODEL_NAME, LLM_API_KEY, LLM_BASE_URL, and LLM_TIMEOUT.
        """
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "").rstrip("/")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        self._validate_config()

    def _validate_config(self):
        if not all([self.model_name, self.api_key, self.base_url]):
            raise ValueError(
                "Missing required LLM configuration. Please set "
                "LLM_MODEL_NAME, LLM_API_KEY, and LLM_BASE_URL in parameters "
                "or in your .env file."
            )

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> Optional[str]:
        """Send a chat request to the LLM and return the response text."""
        print(
            "🧠 Sending think request to LLM "
            f"with provider: {self.provider}, model: {self.model_name}, "
            f"temperature: {temperature}"
        )

        try:
            data = self._chat_completion(messages, temperature=temperature)
            content = data["choices"][0]["message"]["content"]
            print("🧠 Receiving response from LLM...")
            print(content)
            return content
        except Exception as e:
            print(f"Error during LLM think request: {e}")
            return None

    def _chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0) -> dict:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class GeneralLLM(VectorAgentsLLM):
    """Extended LLM client that selects provider-specific configuration."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "gpt")).lower()

        if self.provider in {"gpt", "openai", "openai_compatible"}:
            print(f"Initializing LLM with provider: {self.provider}")
            super().__init__(
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )
            self.provider = "gpt"
            return

        if self.provider == "modelscope":
            print(f"Initializing ModelScope LLM with provider: {self.provider}")
            super().__init__(
                model_name=(
                    model_name
                    or os.getenv("MODELSCOPE_MODEL_NAME")
                    or os.getenv("LLM_MODEL_ID")
                ),
                api_key=api_key or os.getenv("MODELSCOPE_API_KEY"),
                base_url=base_url or os.getenv("MODELSCOPE_BASE_URL"),
                timeout=timeout,
            )
            return

        print(f"Initializing OpenAI-compatible LLM with provider: {self.provider}")
        super().__init__(
            model_name=model_name or os.getenv("LLM_MODEL_NAME"),
            api_key=api_key or os.getenv("LLM_API_KEY"),
            base_url=base_url or os.getenv("LLM_BASE_URL"),
            timeout=timeout,
        )


if __name__ == "__main__":
    try:
        llm = GeneralLLM()
        messages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "介绍一下你是什么模型，并且写一个快速排序算法"},
        ]
        print("--- Sending messages to LLM ---")
        response = llm.think(messages)
        print("\nResponse from LLM:", response)
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
