from typing import Optional, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class CoreLLMSettings(BaseSettings):
    """Shared settings for any LLM provider."""
    temperature: float = 0.7
    max_tokens: int = 1500
    # Add other common parameters like top_p, presence_penalty, frequency_penalty if needed

class OpenAISpecificSettings(CoreLLMSettings):
    api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    model: str = Field("gpt-3.5-turbo", env="DEFAULT_OPENAI_MODEL")
    # You can add more OpenAI specific settings here

class AnthropicSpecificSettings(CoreLLMSettings):
    api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    model: str = Field("claude-2", env="DEFAULT_ANTHROPIC_MODEL")
    # You can add more Anthropic specific settings here

class LMStudioSpecificSettings(CoreLLMSettings):
    # For LMStudio, API key might be optional or a dummy value if the server doesn't require it.
    api_key: Optional[str] = Field("lm-studio-dummy-key", env="LMSTUDIO_API_KEY")
    # Endpoint for LM Studio (or any OpenAI-compatible local server)
    endpoint: str = Field("http://localhost:1234/v1", env="LMSTUDIO_API_ENDPOINT")
    # Model name might be optional if the endpoint serves a specific model or is configured on the server.
    model: Optional[str] = Field(None, env="DEFAULT_LMSTUDIO_MODEL")

class AppSettings(BaseSettings):
    """
    Main application settings.
    These settings will be loaded from environment variables and/or a .env file.
    The environment variable names are derived from the field names (e.g., SELECTED_LLM_PROVIDER).
    """
    selected_llm_provider: str = Field("openai", env="SELECTED_LLM_PROVIDER") # options: 'openai', 'anthropic', 'lmstudio'

    openai: OpenAISpecificSettings = OpenAISpecificSettings()
    anthropic: AnthropicSpecificSettings = AnthropicSpecificSettings()
    lmstudio: LMStudioSpecificSettings = LMStudioSpecificSettings()

    # Define where to load .env file from.
    # model_config is the modern way to set this in Pydantic V2.
    # For Pydantic V1, it was `class Config:` with attributes.
    model_config = SettingsConfigDict(
        env_file='.env',                # Looks for a .env file in the current working directory
        env_file_encoding='utf-8',
        extra='ignore',                 # Ignore extra fields from .env or environment
        env_prefix=''                   # No prefix for env vars, so OPENAI_API_KEY directly maps.
                                        # If you wanted e.g. METAGPT_SYSTEM_OPENAI_API_KEY, set env_prefix='METAGPT_SYSTEM_'
    )

# Global cache for settings
_cached_settings: Optional[AppSettings] = None

def get_settings() -> AppSettings:
    """
    Loads and returns the application settings.
    Settings are loaded once and cached for subsequent calls.
    """
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = AppSettings()
        # You can print a message here if settings are loaded, for debugging
        # print(f"Settings loaded: Provider '{_cached_settings.selected_llm_provider}'")
        # print(f"OpenAI Key loaded: {'Yes' if _cached_settings.openai.api_key else 'No'}")
        # print(f"Anthropic Key loaded: {'Yes' if _cached_settings.anthropic.api_key else 'No'}")
        # print(f"LMStudio Endpoint: {_cached_settings.lmstudio.endpoint}")

    return _cached_settings

# Example of how to use it:
# if __name__ == "__main__":
#     # This will load settings from .env file or environment variables
#     current_settings = get_settings()
#     print(f"Current LLM Provider: {current_settings.selected_llm_provider}")
#     print(f"OpenAI Model: {current_settings.openai.model}")
#     if current_settings.openai.api_key:
#         print(f"OpenAI API Key: {current_settings.openai.api_key[:5]}...") # Print only first 5 chars for security
#     else:
#         print("OpenAI API Key: Not set")

#     print(f"Anthropic Model: {current_settings.anthropic.model}")
#     if current_settings.anthropic.api_key:
#         print(f"Anthropic API Key: {current_settings.anthropic.api_key[:5]}...")
#     else:
#         print("Anthropic API Key: Not set")

#     print(f"LMStudio Endpoint: {current_settings.lmstudio.endpoint}")
#     print(f"LMStudio Model: {current_settings.lmstudio.model if current_settings.lmstudio.model else 'Default/Not Set'}")

    # To use a specific LLM's settings:
    # provider = current_settings.selected_llm_provider
    # if provider == "openai":
    #     llm_config = current_settings.openai
    # elif provider == "anthropic":
    #     llm_config = current_settings.anthropic
    # elif provider == "lmstudio":
    #     llm_config = current_settings.lmstudio
    # else:
    #     raise ValueError(f"Unsupported LLM provider: {provider}")
    # print(f"Selected LLM ({provider}) Model: {llm_config.model}")
    # print(f"Selected LLM ({provider}) Temp: {llm_config.temperature}")
