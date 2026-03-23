"""LLM provider abstraction layer.

Exports the public interface for AI modules to consume:
  - LLMClient: Abstract base class for all providers
  - LLMResponse, LLMUsage: Response data types
  - LLMError: Unified error type
  - create_llm_client: Factory function for explicit provider creation
  - get_llm_client: Settings-driven client creation (main entry point)
  - SUPPORTED_PROVIDERS, DEFAULT_MODELS: Provider metadata
"""
from backend.core import load_kebab_module

# Load kebab-case modules
_client_mod = load_kebab_module("llm/llm-client.py", "llm.llm_client")
_factory_mod = load_kebab_module("llm/llm-client-factory.py", "llm.llm_client_factory")

# Re-export public API
LLMClient = _client_mod.LLMClient
LLMResponse = _client_mod.LLMResponse
LLMUsage = _client_mod.LLMUsage
LLMError = _client_mod.LLMError
create_llm_client = _factory_mod.create_llm_client
get_llm_client = _factory_mod.get_llm_client
SUPPORTED_PROVIDERS = _factory_mod.SUPPORTED_PROVIDERS
DEFAULT_MODELS = _factory_mod.DEFAULT_MODELS

__all__ = [
    "LLMClient",
    "LLMResponse",
    "LLMUsage",
    "LLMError",
    "create_llm_client",
    "get_llm_client",
    "SUPPORTED_PROVIDERS",
    "DEFAULT_MODELS",
]
