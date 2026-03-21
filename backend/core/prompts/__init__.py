"""Prompt modules for TerraBot AI agent.

Kebab-case .py files are loaded via importlib (same pattern as core/__init__.py).
Access prompt functions via the module attributes exposed here:

    from backend.core.prompts import generate_prompt
    system_prompt = generate_prompt.get_prompt(provider="aws")
"""
import importlib.util
import sys
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def _load(filename: str, alias: str):
    """Load a kebab-case .py file and register it under backend.core.prompts.<alias>."""
    full_name = f"backend.core.prompts.{alias}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, _PROMPTS_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate prompt module: {filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


generate_prompt = _load("generate-prompt.py", "generate_prompt")
explain_prompt = _load("explain-prompt.py", "explain_prompt")
diagnose_prompt = _load("diagnose-prompt.py", "diagnose_prompt")
review_prompt = _load("review-prompt.py", "review_prompt")
chat_prompt = _load("chat-prompt.py", "chat_prompt")

__all__ = [
    "generate_prompt",
    "explain_prompt",
    "diagnose_prompt",
    "review_prompt",
    "chat_prompt",
]
