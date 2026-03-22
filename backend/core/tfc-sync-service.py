"""HCP Terraform Cloud sync service.

Provides high-level operations that bridge PowerOps project entities with
TFC workspaces and variables:

  sync_project_to_tfc   — create/update one TFC workspace per project module
  push_variables        — upsert a list of key/value pairs as workspace variables
  generate_cloud_config_block — render the terraform { cloud {} } HCL stanza
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy sibling module loaders
# ---------------------------------------------------------------------------

def _load(rel: str, alias: str):
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    path = _P(__file__).resolve().parent / rel
    spec = _ilu.spec_from_file_location(full, path)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _client_mod():
    return _load("tfc-api-client.py", "tfc_api_client")


def _models_mod():
    return _load("tfc-models.py", "tfc_models")


# ---------------------------------------------------------------------------
# Execution mode detection
# ---------------------------------------------------------------------------

# Providers that must run locally (Proxmox, libvirt, etc.)
_LOCAL_PROVIDERS = {"proxmox", "proxmox-ve", "libvirt", "null"}


def _detect_execution_mode(provider: str) -> str:
    """Return 'local' for self-hosted providers, else 'remote'."""
    return "local" if provider.lower() in _LOCAL_PROVIDERS else "remote"


# ---------------------------------------------------------------------------
# sync_project_to_tfc
# ---------------------------------------------------------------------------

async def sync_project_to_tfc(
    project_id: str,
    tfc_token: str,
    org_name: str,
    modules: list[dict],
    base_url: str = "https://app.terraform.io",
) -> dict[str, Any]:
    """Create or reconcile one TFC workspace per project module.

    Args:
        project_id: PowerOps project UUID (used only for naming/logging).
        tfc_token:  HCP Terraform user/team API token.
        org_name:   TFC organisation name to create workspaces in.
        modules:    List of dicts with keys: name, provider, path.
        base_url:   TFC base URL (override for TFE).

    Returns:
        dict with 'created', 'updated', 'skipped' lists of workspace names.
    """
    _cm = _client_mod()
    client = _cm.TFCClient(token=tfc_token, base_url=base_url)

    # Fetch existing workspaces to avoid duplicates
    try:
        existing_ws = await client.list_workspaces(org_name)
    except _cm.TFCAPIError as exc:
        raise RuntimeError(f"Failed to list TFC workspaces: {exc}") from exc

    existing_by_name: dict[str, Any] = {ws.name: ws for ws in existing_ws}

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    for mod in modules:
        name: str = mod.get("name", "")
        provider: str = mod.get("provider", "")
        execution_mode = _detect_execution_mode(provider)

        if not name:
            logger.warning("Skipping module with empty name in project %s", project_id)
            continue

        try:
            if name in existing_by_name:
                # Update execution mode if it differs
                ws = existing_by_name[name]
                if ws.execution_mode != execution_mode:
                    await client.update_workspace(ws.id, execution_mode=execution_mode)
                    updated.append(name)
                    logger.info("Updated TFC workspace %s (execution_mode=%s)", name, execution_mode)
                else:
                    skipped.append(name)
            else:
                await client.create_workspace(
                    org=org_name,
                    name=name,
                    execution_mode=execution_mode,
                    auto_apply=False,
                )
                created.append(name)
                logger.info("Created TFC workspace %s (execution_mode=%s)", name, execution_mode)
        except _cm.TFCAPIError as exc:
            logger.error("TFC error for module %s: %s", name, exc)
            # Continue processing remaining modules
            skipped.append(name)

    return {"created": created, "updated": updated, "skipped": skipped}


# ---------------------------------------------------------------------------
# push_variables
# ---------------------------------------------------------------------------

async def push_variables(
    ws_id: str,
    vars_list: list[dict],
    tfc_token: str,
    base_url: str = "https://app.terraform.io",
) -> dict[str, Any]:
    """Upsert a list of variables into a TFC workspace.

    Each entry in vars_list must have:
      - key (str)
      - value (str)
    Optional keys:
      - category: 'terraform' (default) | 'env'
      - sensitive: bool (default False)
      - description: str
      - hcl: bool (default False)

    Returns:
        dict with 'created', 'updated' lists of variable keys.
    """
    _cm = _client_mod()
    client = _cm.TFCClient(token=tfc_token, base_url=base_url)

    try:
        existing_vars = await client.list_variables(ws_id)
    except _cm.TFCAPIError as exc:
        raise RuntimeError(f"Failed to list TFC variables for workspace {ws_id}: {exc}") from exc

    existing_by_key: dict[str, Any] = {v.key: v for v in existing_vars}

    created: list[str] = []
    updated: list[str] = []

    for var in vars_list:
        key = var.get("key", "")
        value = str(var.get("value", ""))
        category = var.get("category", "terraform")
        sensitive = bool(var.get("sensitive", False))
        description = str(var.get("description", ""))
        hcl = bool(var.get("hcl", False))

        if not key:
            logger.warning("Skipping variable entry with empty key in workspace %s", ws_id)
            continue

        try:
            if key in existing_by_key:
                existing = existing_by_key[key]
                await client.update_variable(ws_id, existing.id, value=value, sensitive=sensitive)
                updated.append(key)
            else:
                await client.create_variable(
                    ws_id=ws_id,
                    key=key,
                    value=value,
                    category=category,
                    sensitive=sensitive,
                    description=description,
                    hcl=hcl,
                )
                created.append(key)
        except _cm.TFCAPIError as exc:
            logger.error("Failed to upsert variable %s in workspace %s: %s", key, ws_id, exc)

    return {"created": created, "updated": updated}


# ---------------------------------------------------------------------------
# generate_cloud_config_block
# ---------------------------------------------------------------------------

def generate_cloud_config_block(org: str, workspace_name: str) -> str:
    """Render the terraform { cloud {} } HCL block for a given workspace.

    The rendered block can be written to a terraform.tf file so that
    Terraform CLI uses TFC as the remote backend automatically.

    Example output:
        terraform {
          cloud {
            organization = "acme-corp"
            workspaces {
              name = "my-workspace"
            }
          }
        }
    """
    if not org:
        raise ValueError("org must not be empty")
    if not workspace_name:
        raise ValueError("workspace_name must not be empty")

    return (
        f'terraform {{\n'
        f'  cloud {{\n'
        f'    organization = "{org}"\n'
        f'    workspaces {{\n'
        f'      name = "{workspace_name}"\n'
        f'    }}\n'
        f'  }}\n'
        f'}}\n'
    )
