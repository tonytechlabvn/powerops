"""TerraBot core engine — importable without FastAPI/Typer dependency.

Kebab-case Python files cannot be imported via standard dotted-path syntax.
This module loads them via importlib and registers them in sys.modules so
the rest of the package can do:

    from backend.core import terraform_runner
    runner = terraform_runner.TerraformRunner(...)
"""
import importlib.util
import sys
from pathlib import Path

_CORE_DIR = Path(__file__).parent


def load_kebab_module(filename: str, alias: str):
    """Load a kebab-case .py file and register it under backend.core.<alias>.

    Idempotent — returns cached module if already loaded.
    """
    full_name = f"backend.core.{alias}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, _CORE_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate module file: {filename}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# Pre-load all kebab-case modules so callers can import them as attributes
subprocess_executor = load_kebab_module("subprocess-executor.py", "subprocess_executor")
terraform_runner    = load_kebab_module("terraform-runner.py",    "terraform_runner")
hcl_validator       = load_kebab_module("hcl-validator.py",       "hcl_validator")
template_engine     = load_kebab_module("template-engine.py",     "template_engine")
cost_estimator      = load_kebab_module("cost-estimator.py",      "cost_estimator")
ai_agent_helpers    = load_kebab_module("ai-agent-helpers.py",    "ai_agent_helpers")
ai_agent            = load_kebab_module("ai-agent.py",            "ai_agent")

# Phase 7 — advanced feature modules
workspace_manager   = load_kebab_module("workspace-manager.py",   "workspace_manager")
drift_detector      = load_kebab_module("drift-detector.py",      "drift_detector")
import_wizard       = load_kebab_module("import-wizard.py",       "import_wizard")

from backend.core.config import Settings, get_settings  # noqa: E402
from backend.core import models, exceptions              # noqa: E402

__all__ = [
    "Settings",
    "get_settings",
    "models",
    "exceptions",
    "subprocess_executor",
    "terraform_runner",
    "hcl_validator",
    "template_engine",
    "cost_estimator",
    "ai_agent_helpers",
    "ai_agent",
    "workspace_manager",
    "drift_detector",
    "import_wizard",
    "load_kebab_module",
]
