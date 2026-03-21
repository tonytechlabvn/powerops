"""Core explain engine for Terraform resources, plan output, and HCL blocks.

Resource type data lives in explainer-resource-data.py (loaded via importlib).
Static knowledge covers the top 20 resource types; unknown types get a
structured fallback description derived from the type name.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from backend.learning.glossary import get_concept

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load kebab-case resource data module
# ---------------------------------------------------------------------------

_DATA_MODULE_NAME = "backend.learning.explainer_resource_data"
_DATA_MODULE_FILE = Path(__file__).parent / "explainer-resource-data.py"


def _load_data_module():
    if _DATA_MODULE_NAME in sys.modules:
        return sys.modules[_DATA_MODULE_NAME]
    spec = importlib.util.spec_from_file_location(_DATA_MODULE_NAME, _DATA_MODULE_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate explainer-resource-data.py at {_DATA_MODULE_FILE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_DATA_MODULE_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_data = _load_data_module()

_RESOURCE_EXPLANATIONS: dict[str, dict] = _data.RESOURCE_EXPLANATIONS
_DESTRUCTIVE_ACTIONS: frozenset[str] = _data.DESTRUCTIVE_ACTIONS
_ACTION_LABELS: dict[str, str] = _data.ACTION_LABELS


# ---------------------------------------------------------------------------
# Explainer class
# ---------------------------------------------------------------------------


class Explainer:
    """Explains Terraform resources, plan output, and HCL blocks.

    All methods are stateless and safe to call without instantiation state.
    """

    # ------------------------------------------------------------------
    # Resource type explanations
    # ------------------------------------------------------------------

    def explain_resource(self, resource_type: str) -> dict:
        """Return a structured explanation for a Terraform resource type.

        Args:
            resource_type: e.g. "aws_instance", "proxmox_vm_qemu".

        Returns:
            Dict: resource_type, title, what, key_args, cost_note, docs,
            is_static (True when a hand-authored entry exists).
        """
        entry = _RESOURCE_EXPLANATIONS.get(resource_type)
        if entry:
            return {"resource_type": resource_type, "is_static": True, **entry}

        # Fallback — derive readable name and provider from type string
        provider = resource_type.split("_")[0] if "_" in resource_type else "unknown"
        readable = resource_type.replace("_", " ").title()
        return {
            "resource_type": resource_type,
            "title": readable,
            "what": f"A {readable} resource managed by the '{provider}' provider.",
            "key_args": [],
            "cost_note": "Refer to your provider's pricing documentation.",
            "docs": f"https://registry.terraform.io/providers/hashicorp/{provider}/latest/docs",
            "is_static": False,
        }

    # ------------------------------------------------------------------
    # Plan output annotations
    # ------------------------------------------------------------------

    def explain_plan_output(self, plan_json: dict) -> list[dict]:
        """Annotate each resource change in a terraform plan JSON.

        Accepts either raw 'terraform show -json' output (with nested
        change.actions lists) or a pre-parsed dict with a flat
        'resource_changes' list of ResourceChange-like dicts.

        Returns:
            List of annotation dicts per resource change, each with:
            address, action, action_label, what, why, cost_impact,
            is_destructive, warning.
        """
        raw_changes: list[dict] = []
        if "resource_changes" in plan_json:
            raw_changes = plan_json["resource_changes"]
        elif isinstance(plan_json, list):
            raw_changes = plan_json  # type: ignore[assignment]

        return [self._annotate_change(c) for c in raw_changes]

    # ------------------------------------------------------------------
    # HCL block explainer
    # ------------------------------------------------------------------

    def explain_hcl_block(self, hcl: str) -> str:
        """Return a plain-English explanation of an HCL snippet.

        Performs static pattern matching on each line; no external API call.

        Args:
            hcl: Raw HCL string (one or more blocks).

        Returns:
            Multi-line human-readable explanation string.
        """
        if not hcl or not hcl.strip():
            return "Empty HCL — nothing to explain."

        lines = [self._explain_hcl_line(l.strip()) for l in hcl.strip().splitlines()]
        explanations = [e for e in lines if e]

        if not explanations:
            return "This HCL block defines Terraform configuration. Use terraform validate to check syntax."
        return "\n".join(explanations)

    # ------------------------------------------------------------------
    # Glossary lookup delegation
    # ------------------------------------------------------------------

    def get_concept(self, term: str) -> dict | None:
        """Look up a Terraform concept from the static glossary.

        Args:
            term: Concept name (case-insensitive), e.g. "state", "provider".

        Returns:
            Full concept dict or None if not found.
        """
        return get_concept(term)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _annotate_change(self, change: dict) -> dict[str, Any]:
        """Build one annotation dict from a raw resource change entry."""
        address = change.get("address", "unknown")

        # Handle both raw plan JSON (change.change.actions list) and model dicts
        if "change" in change and isinstance(change["change"], dict):
            actions = change["change"].get("actions", [])
            action = self._normalise_action(actions)
        else:
            action = change.get("action", "no-op")

        resource_type = change.get("type", address.split(".")[0] if "." in address else "")
        explanation = self.explain_resource(resource_type)
        is_destructive = action in _DESTRUCTIVE_ACTIONS
        action_label = _ACTION_LABELS.get(action, action)

        return {
            "address": address,
            "action": action,
            "action_label": action_label,
            "what": f"{explanation['title']} ({address}) {action_label}.",
            "why": self._infer_why(action, resource_type),
            "cost_impact": explanation.get("cost_note", ""),
            "is_destructive": is_destructive,
            "warning": (
                f"DESTRUCTIVE: '{address}' will be {action}d. "
                "Verify this is intentional before applying."
                if is_destructive else ""
            ),
        }

    @staticmethod
    def _normalise_action(actions: list[str]) -> str:
        """Convert a plan JSON actions list to a single action string."""
        if not actions:
            return "no-op"
        if "delete" in actions and "create" in actions:
            return "replace"
        return actions[0]

    @staticmethod
    def _infer_why(action: str, resource_type: str) -> str:
        """Return a plain-English reason for the given change action."""
        reasons = {
            "create":  (f"This {resource_type} does not exist in the current state "
                        "and will be provisioned for the first time."),
            "update":  (f"One or more attributes of this {resource_type} differ from "
                        "the current state and will be updated in-place."),
            "delete":  (f"This {resource_type} is no longer in the configuration "
                        "and will be removed from your infrastructure."),
            "replace": (f"A required attribute of this {resource_type} changed in a "
                        "way that forces recreation — the old resource is deleted first."),
            "no-op":   f"This {resource_type} matches the desired state — no changes needed.",
            "read":    f"This data source reads existing {resource_type} information from the provider.",
        }
        return reasons.get(action, f"Change action: {action}.")

    @staticmethod
    def _explain_hcl_line(line: str) -> str:
        """Return a short explanation for one HCL line, or empty string."""
        if not line or line.startswith("#"):
            return ""
        if line.startswith("terraform {"):
            return "terraform block: configures Terraform version and required providers."
        if line.startswith("provider "):
            name = line.split('"')[1] if '"' in line else "unknown"
            return f"provider block: configures the '{name}' provider plugin."
        if line.startswith("resource "):
            parts = line.split('"')
            if len(parts) >= 4:
                return f"resource block: declares a '{parts[1]}' named '{parts[3]}'."
        if line.startswith("data "):
            parts = line.split('"')
            if len(parts) >= 4:
                return f"data block: reads existing '{parts[1]}' data named '{parts[3]}'."
        if line.startswith("variable "):
            name = line.split('"')[1] if '"' in line else "unknown"
            return f"variable block: declares input variable '{name}'."
        if line.startswith("output "):
            name = line.split('"')[1] if '"' in line else "unknown"
            return f"output block: exports value '{name}' after apply."
        if line.startswith("module "):
            name = line.split('"')[1] if '"' in line else "unknown"
            return f"module block: calls child module '{name}'."
        if line.startswith("locals {"):
            return "locals block: defines named local expressions to reduce repetition."
        if "=" in line and not line.startswith("}"):
            key = line.split("=")[0].strip()
            return f"  {key}: sets the '{key}' argument."
        return ""
