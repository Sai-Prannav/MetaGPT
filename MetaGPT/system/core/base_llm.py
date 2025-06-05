from abc import ABC, abstractmethod
from typing import Optional, Iterator, Any, Dict

class BaseLLM(ABC):
    def __init__(self, model_name: str, api_key: Optional[str] = None, endpoint: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key
        self.endpoint = endpoint # For local LLMs like LM Studio or Ollama compatible endpoints
        self.config_params = kwargs # For other LLM specific params

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generates a response from the LLM based on the prompt."""
        pass

    async def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """
        Generates a streaming response from the LLM.
        This is optional and might not be supported by all LLM backends.
        If not overridden, it can call the non-streaming generate.
        """
        # Default implementation calls the non-streaming version and yields its single result.
        # Concrete classes that support streaming should override this.
        response = await self.generate(prompt, **kwargs)
        yield response

    # Potential additional methods:
    # - get_model_info() -> Dict[str, Any]
    # - count_tokens(text: str) -> int
