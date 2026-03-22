"""Unit tests for tfc-models.py and tfc-sync-service.py.

Covers:
- JSON:API envelope helpers (parse_jsonapi, parse_jsonapi_list)
- TFCOrg / TFCWorkspace / TFCVariable / TFCRun model construction
- generate_cloud_config_block HCL rendering
- _detect_execution_mode provider detection
- sync_project_to_tfc and push_variables logic (TFCClient mocked)
"""
from __future__ import annotations

import importlib.util as _ilu
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to load kebab-case modules under test
# ---------------------------------------------------------------------------

_CORE = Path(__file__).resolve().parent.parent.parent.parent / "backend" / "core"


def _load(filename: str, alias: str):
    full = f"backend.core.{alias}"
    if full in sys.modules:
        return sys.modules[full]
    spec = _ilu.spec_from_file_location(full, _CORE / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def models():
    return _load("tfc-models.py", "tfc_models")


@pytest.fixture(scope="module")
def sync_svc():
    svc = _load("tfc-sync-service.py", "tfc_sync_service")
    # Eagerly load the client module so sys.modules is populated before tests patch it
    _load("tfc-api-client.py", "tfc_api_client")
    return svc


# ---------------------------------------------------------------------------
# parse_jsonapi helpers
# ---------------------------------------------------------------------------


def test_parse_jsonapi_extracts_id_and_attrs(models):
    data = {
        "data": {
            "id": "ws-abc123",
            "type": "workspaces",
            "attributes": {"name": "my-ws", "execution-mode": "remote"},
        }
    }
    flat = models.parse_jsonapi(data)
    assert flat["id"] == "ws-abc123"
    assert flat["name"] == "my-ws"
    assert flat["execution-mode"] == "remote"


def test_parse_jsonapi_hoists_relationship_id(models):
    data = {
        "data": {
            "id": "run-1",
            "type": "runs",
            "attributes": {"status": "planned"},
            "relationships": {
                "workspace": {"data": {"id": "ws-xyz", "type": "workspaces"}}
            },
        }
    }
    flat = models.parse_jsonapi(data)
    assert flat["workspace_id"] == "ws-xyz"


def test_parse_jsonapi_list_returns_list(models):
    data = {
        "data": [
            {"id": "ws-1", "type": "workspaces", "attributes": {"name": "alpha"}},
            {"id": "ws-2", "type": "workspaces", "attributes": {"name": "beta"}},
        ]
    }
    items = models.parse_jsonapi_list(data)
    assert len(items) == 2
    assert items[0]["name"] == "alpha"
    assert items[1]["id"] == "ws-2"


def test_parse_jsonapi_tolerates_pre_extracted_resource(models):
    """parse_jsonapi should work when passed the inner resource dict directly."""
    resource = {"id": "org-1", "type": "organizations", "attributes": {"name": "acme"}}
    flat = models.parse_jsonapi(resource)
    assert flat["id"] == "org-1"
    assert flat["name"] == "acme"


# ---------------------------------------------------------------------------
# TFCOrg
# ---------------------------------------------------------------------------


def test_tfc_org_from_jsonapi(models):
    data = {
        "data": {
            "id": "acme",
            "type": "organizations",
            "attributes": {"name": "acme", "email": "admin@acme.io"},
        }
    }
    org = models.TFCOrg.from_jsonapi(data)
    assert org.id == "acme"
    assert org.name == "acme"
    assert org.email == "admin@acme.io"


# ---------------------------------------------------------------------------
# TFCWorkspace
# ---------------------------------------------------------------------------


def test_tfc_workspace_defaults(models):
    data = {
        "data": {
            "id": "ws-abc",
            "type": "workspaces",
            "attributes": {"name": "staging"},
        }
    }
    ws = models.TFCWorkspace.from_jsonapi(data, org_name="myorg")
    assert ws.id == "ws-abc"
    assert ws.name == "staging"
    assert ws.org_name == "myorg"
    assert ws.execution_mode == "remote"
    assert ws.auto_apply is False
    assert ws.locked is False


def test_tfc_workspace_local_mode(models):
    data = {
        "data": {
            "id": "ws-local",
            "type": "workspaces",
            "attributes": {"name": "proxmox-ws", "execution-mode": "local", "auto-apply": True},
        }
    }
    ws = models.TFCWorkspace.from_jsonapi(data)
    assert ws.execution_mode == "local"
    assert ws.auto_apply is True


# ---------------------------------------------------------------------------
# TFCVariable
# ---------------------------------------------------------------------------


def test_tfc_variable_sensitive(models):
    data = {
        "data": {
            "id": "var-1",
            "type": "vars",
            "attributes": {
                "key": "AWS_SECRET_KEY",
                "value": "",
                "category": "env",
                "sensitive": True,
            },
        }
    }
    var = models.TFCVariable.from_jsonapi(data)
    assert var.key == "AWS_SECRET_KEY"
    assert var.sensitive is True
    assert var.category == "env"


# ---------------------------------------------------------------------------
# TFCRun
# ---------------------------------------------------------------------------


def test_tfc_run_from_jsonapi(models):
    data = {
        "data": {
            "id": "run-xyz",
            "type": "runs",
            "attributes": {"status": "planned", "message": "CI run", "auto-apply": False},
            "relationships": {
                "workspace": {"data": {"id": "ws-abc", "type": "workspaces"}}
            },
        }
    }
    run = models.TFCRun.from_jsonapi(data)
    assert run.id == "run-xyz"
    assert run.status == "planned"
    assert run.workspace_id == "ws-abc"


# ---------------------------------------------------------------------------
# generate_cloud_config_block
# ---------------------------------------------------------------------------


def test_generate_cloud_config_block_renders_hcl(sync_svc):
    hcl = sync_svc.generate_cloud_config_block("acme", "my-workspace")
    assert 'organization = "acme"' in hcl
    assert 'name = "my-workspace"' in hcl
    assert "terraform {" in hcl
    assert "cloud {" in hcl


def test_generate_cloud_config_block_rejects_empty_org(sync_svc):
    with pytest.raises(ValueError, match="org must not be empty"):
        sync_svc.generate_cloud_config_block("", "ws")


def test_generate_cloud_config_block_rejects_empty_name(sync_svc):
    with pytest.raises(ValueError, match="workspace_name must not be empty"):
        sync_svc.generate_cloud_config_block("myorg", "")


# ---------------------------------------------------------------------------
# _detect_execution_mode
# ---------------------------------------------------------------------------


def test_detect_execution_mode_proxmox_is_local(sync_svc):
    assert sync_svc._detect_execution_mode("proxmox") == "local"
    assert sync_svc._detect_execution_mode("PROXMOX") == "local"


def test_detect_execution_mode_aws_is_remote(sync_svc):
    assert sync_svc._detect_execution_mode("aws") == "remote"
    assert sync_svc._detect_execution_mode("azurerm") == "remote"
    assert sync_svc._detect_execution_mode("google") == "remote"


def test_detect_execution_mode_libvirt_is_local(sync_svc):
    assert sync_svc._detect_execution_mode("libvirt") == "local"


# ---------------------------------------------------------------------------
# sync_project_to_tfc (mocked TFCClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_creates_new_workspaces(sync_svc, models):
    """New modules should result in create_workspace calls."""
    mock_client = MagicMock()
    mock_client.list_workspaces = AsyncMock(return_value=[])
    mock_client.create_workspace = AsyncMock(
        return_value=models.TFCWorkspace(id="ws-new", name="vpc", execution_mode="remote", auto_apply=False, locked=False)
    )

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.sync_project_to_tfc(
            project_id="proj-1",
            tfc_token="tok",
            org_name="acme",
            modules=[{"name": "vpc", "provider": "aws", "path": "modules/vpc"}],
        )

    assert "vpc" in result["created"]
    assert result["updated"] == []
    mock_client.create_workspace.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_updates_when_execution_mode_differs(sync_svc, models):
    """Existing workspace with wrong execution_mode should be updated."""
    existing = models.TFCWorkspace(
        id="ws-existing", name="proxmox-vm", execution_mode="remote",
        auto_apply=False, locked=False,
    )
    mock_client = MagicMock()
    mock_client.list_workspaces = AsyncMock(return_value=[existing])
    mock_client.update_workspace = AsyncMock(return_value=existing)

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.sync_project_to_tfc(
            project_id="proj-1",
            tfc_token="tok",
            org_name="acme",
            modules=[{"name": "proxmox-vm", "provider": "proxmox", "path": "modules/vm"}],
        )

    assert "proxmox-vm" in result["updated"]
    mock_client.update_workspace.assert_awaited_once_with("ws-existing", execution_mode="local")


@pytest.mark.asyncio
async def test_sync_skips_when_execution_mode_matches(sync_svc, models):
    """No update when execution mode is already correct."""
    existing = models.TFCWorkspace(
        id="ws-ok", name="network", execution_mode="remote",
        auto_apply=False, locked=False,
    )
    mock_client = MagicMock()
    mock_client.list_workspaces = AsyncMock(return_value=[existing])

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.sync_project_to_tfc(
            project_id="proj-1",
            tfc_token="tok",
            org_name="acme",
            modules=[{"name": "network", "provider": "aws", "path": "modules/net"}],
        )

    assert "network" in result["skipped"]
    assert result["created"] == []
    assert result["updated"] == []


# ---------------------------------------------------------------------------
# push_variables (mocked TFCClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_variables_creates_new(sync_svc, models):
    mock_client = MagicMock()
    mock_client.list_variables = AsyncMock(return_value=[])
    mock_client.create_variable = AsyncMock(
        return_value=models.TFCVariable(id="var-1", key="region", value="us-east-1", category="terraform", sensitive=False)
    )

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.push_variables(
            ws_id="ws-abc",
            vars_list=[{"key": "region", "value": "us-east-1"}],
            tfc_token="tok",
        )

    assert "region" in result["created"]
    assert result["updated"] == []


@pytest.mark.asyncio
async def test_push_variables_updates_existing(sync_svc, models):
    existing_var = models.TFCVariable(
        id="var-99", key="region", value="eu-west-1",
        category="terraform", sensitive=False,
    )
    mock_client = MagicMock()
    mock_client.list_variables = AsyncMock(return_value=[existing_var])
    mock_client.update_variable = AsyncMock(return_value=existing_var)

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.push_variables(
            ws_id="ws-abc",
            vars_list=[{"key": "region", "value": "ap-southeast-1"}],
            tfc_token="tok",
        )

    assert "region" in result["updated"]
    mock_client.update_variable.assert_awaited_once_with(
        "ws-abc", "var-99", value="ap-southeast-1", sensitive=False
    )


@pytest.mark.asyncio
async def test_push_variables_skips_empty_key(sync_svc, models):
    mock_client = MagicMock()
    mock_client.list_variables = AsyncMock(return_value=[])

    with patch.object(
        sys.modules["backend.core.tfc_api_client"],
        "TFCClient",
        return_value=mock_client,
    ):
        result = await sync_svc.push_variables(
            ws_id="ws-abc",
            vars_list=[{"key": "", "value": "ignored"}],
            tfc_token="tok",
        )

    assert result["created"] == []
    assert result["updated"] == []
