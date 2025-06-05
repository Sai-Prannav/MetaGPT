# Modular Backend Replica Design

## 1. Overall Architecture

**Goal:** To create a local, CLI-based, single-user, Python-exclusive, modular MetaGPT backend replica.

The core principle of this design is **modularity**. Each key component (LLM interaction, memory, agent capabilities, communication) will be implemented as a replaceable module with a well-defined interface. This allows for:

*   **Plug-and-Play Components:** Easily swap out different LLM providers (OpenAI, Anthropic, local models via LM Studio), memory systems, or even agent implementations.
*   **Simplified Development:** Focus on individual components without tight coupling to the rest of the system.
*   **Testability:** Individual modules can be unit-tested in isolation.
*   **Extensibility:** New functionalities or integrations can be added by implementing new modules that conform to the defined interfaces.

The system will initially focus on a single-agent interaction model driven by CLI commands, but the modularity should allow for future expansion to multi-agent scenarios if desired.

## 2. Directory Structure for `MetaGPT/system/`

The proposed directory structure aims for clarity and separation of concerns:

```
MetaGPT/system/
├── core/                  # Core interfaces and base classes
│   ├── __init__.py
│   ├── base_agent.py
│   ├── base_llm.py
│   ├── base_memory.py
│   ├── base_communication.py
│   └── event_bus.py       # Simple event bus for decoupling
├── agents/                # Concrete agent implementations
│   ├── __init__.py
│   └── general_agent.py   # Example initial agent
├── llm_integrations/      # LLM API integrations
│   ├── __init__.py
│   ├── openai_llm.py
│   ├── anthropic_llm.py
│   └── lmstudio_llm.py    # For local models via LM Studio/Ollama etc.
├── memory/                # Memory component implementations
│   ├── __init__.py
│   └── simple_memory.py
├── communication/         # Communication layer implementations
│   ├── __init__.py
│   └── cli_communication.py # For CLI input/output
├── tasks/                 # Task definition and execution logic (optional, can be part of agent)
│   ├── __init__.py
│   └── base_task.py
├── cli/                   # Command-line interface logic
│   ├── __init__.py
│   └── main.py
├── utils/                 # Utility functions and shared constants
│   ├── __init__.py
│   └── helpers.py
├── configs/               # Configuration management
│   ├── __init__.py
│   ├── default_config.yaml # Default configuration values
│   └── settings.py        # Pydantic settings model
└── tests/                 # Test suites (mirroring structure)
    ├── __init__.py
    ├── core/
    ├── agents/
    ├── llm_integrations/
    ├── memory/
    └── communication/
```
*   `__init__.py` files will be added to each directory to make them Python packages.

## 3. Core Interfaces/Abstract Base Classes (in `MetaGPT/system/core/`)

These ABCs will define the contracts for each modular component.

### `base_agent.py`
```python
from abc import ABC, abstractmethod
from typing import Any
from .base_llm import BaseLLM
from .base_memory import BaseMemory

class BaseAgent(ABC):
    def __init__(self, name: str, llm: BaseLLM, memory: BaseMemory):
        self.name = name
        self.llm = llm
        self.memory = memory

    @abstractmethod
    async def process_message(self, message: Any) -> Any:
        """Processes an incoming message and returns a response."""
        pass

    @abstractmethod
    async def execute_task(self, task_description: str) -> Any:
        """Executes a given task and returns the result."""
        pass

    # Potential additional methods:
    # - load_persona(persona_description: str)
    # - set_goal(goal: str)
```

### `base_llm.py`
```python
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
        yield await self.generate(prompt, **kwargs)

    # Potential additional methods:
    # - get_model_info() -> Dict[str, Any]
    # - count_tokens(text: str) -> int
```

### `base_memory.py`
```python
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict # Dict for structured messages

class BaseMemory(ABC):
    @abstractmethod
    async def add_message(self, message_content: Any, role: str, metadata: Optional[Dict] = None):
        """Adds a message to the memory, role indicates sender (e.g., 'user', 'assistant', 'system')."""
        pass

    @abstractmethod
    async def get_history(self, max_messages: Optional[int] = None) -> List[Any]:
        """Retrieves the message history, optionally limited to the last max_messages."""
        pass

    @abstractmethod
    async def clear(self):
        """Clears all messages from the memory."""
        pass

    # Potential additional methods:
    # - search(query: str) -> List[Any]
    # - save_to_disk(path: str)
    # - load_from_disk(path: str)
```

### `base_communication.py`
```python
from abc import ABC, abstractmethod

class BaseCommunication(ABC):
    @abstractmethod
    async def get_input(self, prompt_message: str = "> ") -> str:
        """Gets input from the user (e.g., via CLI)."""
        pass

    @abstractmethod
    async def send_output(self, message: str, **kwargs): # Add kwargs for color, formatting etc.
        """Sends output to the user (e.g., prints to CLI)."""
        pass
```

### `event_bus.py` (Concrete Class)
This provides a simple mechanism for components to signal events without direct coupling. For instance, an LLM integration might publish an event when an API call fails, or the CLI might publish an event when a new command is received.

```python
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event_type: str, data: Any = None):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                # Consider if callbacks should be async and awaited
                if inspect.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data) # For synchronous callbacks

# Could be a singleton instance or passed via dependency injection.
# import inspect # Required for checking if callback is async
```

## 4. Configuration System (`MetaGPT/system/configs/settings.py`)

We will use Pydantic's `BaseSettings` for a robust and type-safe configuration system.

### `settings.py`
```python
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class LLMSettings(BaseSettings):
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    endpoint: Optional[str] = None # e.g., "http://localhost:1234/v1" for LM Studio
    temperature: float = 0.7
    max_tokens: int = 1500

class OpenAISettings(LLMSettings):
    model: str = "gpt-3.5-turbo"
    # api_key will be inherited

class AnthropicSettings(LLMSettings):
    model: str = "claude-2"
    # api_key will be inherited

class LMStudioSettings(LLMSettings):
    model: Optional[str] = None # Model name might not be needed if endpoint handles it
    endpoint: str = "http://localhost:1234/v1"

class AppSettings(BaseSettings):
    # Define application-wide settings here
    selected_llm_provider: str = "openai" # 'openai', 'anthropic', 'lmstudio'

    openai_settings: OpenAISettings = OpenAISettings()
    anthropic_settings: AnthropicSettings = AnthropicSettings()
    lmstudio_settings: LMStudioSettings = LMStudioSettings()

    # Example of a setting for memory
    memory_type: str = "simple" # 'simple', 'persistent_json', etc.

    # Configuration for loading from .env file and respecting environment variables
    # Pydantic-settings will automatically look for .env files and environment variables.
    # Prefix for environment variables can be set if needed, e.g., METAGPT_SYSTEM_
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


# Global config instance, can be imported by other modules
# The settings will be loaded when this module is imported.
# Actual loading from .env or environment variables happens when AppSettings() is called.
# It's better to have a function to get settings to control when it's loaded.

_cached_settings: Optional[AppSettings] = None

def get_settings() -> AppSettings:
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = AppSettings()
    return _cached_settings

# Example: MetaGPT/system/configs/default_config.yaml (if YAML is preferred over .env for defaults)
# openai_settings:
#   model: "gpt-4-turbo-preview"
# anthropic_settings:
#   model: "claude-3-opus-20240229"
# selected_llm_provider: "openai"

# Pydantic settings can also load from YAML if combined with a custom settings source.
# For simplicity, .env and environment variables are the primary method.
```
Configuration will be loadable from:
1.  Environment variables (highest precedence).
2.  A `.env` file in the project root or `MetaGPT/system/` directory.
3.  Default values defined in the Pydantic models themselves.

A `default_config.yaml` could be provided as a template, but Pydantic's `.env` handling is often sufficient.

## 5. CLI Entry Point (`MetaGPT/system/cli/main.py`)

The CLI will be the primary way to interact with this local backend.

### `main.py`
*   **Library:** `typer` or `click` will be used for creating a clean command-line interface. `typer` is often preferred for its Pydantic integration and modern Python feel.
*   **Initialization:**
    *   Load configuration using `configs.settings.get_settings()`.
    *   Instantiate the chosen `BaseCommunication` (e.g., `CLICommunication`).
    *   Instantiate the chosen `BaseMemory` (e.g., `SimpleMemory`).
    *   Instantiate the chosen `BaseLLM` based on configuration (e.g., `OpenAILLM`, `AnthropicLLM`, `LMStudioLLM`).
    *   Instantiate the `BaseAgent` (e.g., `GeneralAgent`) with the LLM and Memory components.
*   **Initial Commands:**
    *   `run (ctx: typer.Context, task_description: str)`:
        *   Takes a task description from the user.
        *   Passes it to the agent's `execute_task` method.
        *   The agent interacts with the LLM and its memory.
        *   Results are displayed via the `Communication` module.
    *   `chat (ctx: typer.Context)`:
        *   Starts an interactive chat session with the agent.
        *   Uses `agent.process_message()` for each user input.
    *   `configure (ctx: typer.Context, setting_path: str, value: str)`:
        *   Allows viewing and potentially updating configuration settings (e.g., `configure selected_llm_provider lmstudio`).
        *   This might involve modifying a user-specific config file or guiding the user to set environment variables.
    *   `test-llm (ctx: typer.Context)`:
        *   A utility command to send a simple test prompt to the configured LLM to verify connectivity and API key validity.

Example using `typer`:
```python
# import typer
# from ..configs.settings import get_settings
# from ..agents.general_agent import GeneralAgent
# from ..llm_integrations.openai_llm import OpenAILLM # and others
# from ..memory.simple_memory import SimpleMemory
# from ..communication.cli_communication import CLICommunication
# # ... and other factory functions or direct instantiations based on settings

# app = typer.Typer()

# @app.command()
# def run(task_description: str):
#     settings = get_settings()
#     comm = CLICommunication()
#     mem = SimpleMemory() # Or load based on settings.memory_type

#     # LLM Factory based on settings.selected_llm_provider
#     llm = None
#     if settings.selected_llm_provider == "openai":
#         llm = OpenAILLM(model_name=settings.openai_settings.model, api_key=settings.openai_settings.api_key)
#     elif settings.selected_llm_provider == "lmstudio":
#         llm = LMStudioLLM(endpoint=settings.lmstudio_settings.endpoint, model_name=settings.lmstudio_settings.model)
#     # ... add other providers
#     else:
#         comm.send_output(f"Error: Unknown LLM provider '{settings.selected_llm_provider}'")
#         raise typer.Exit(code=1)

#     if not llm:
#         comm.send_output("LLM could not be initialized.")
#         raise typer.Exit(code=1)

#     agent = GeneralAgent(name="LocalAgent", llm=llm, memory=mem)

#     comm.send_output(f"Executing task: {task_description}")
#     # result = await agent.execute_task(task_description) # If async
#     # For typer, need to handle async if used. Typer supports async commands.
#     # comm.send_output(f"Task result: {result}")
#     # For now, keeping it conceptual. Actual implementation will handle async.
#     pass

# @app.command()
# def chat():
#    # Similar setup, then loop for interactive chat
#    pass

# @app.command()
# def configure(setting_path: str, value: str):
#     # Logic to update configuration (e.g., save to a user config yaml)
#     pass

# if __name__ == "__main__":
#    app()
```

This design provides a solid foundation for building the modular backend replica. The next steps would involve implementing these core interfaces and then building out the concrete classes for each component.
```
