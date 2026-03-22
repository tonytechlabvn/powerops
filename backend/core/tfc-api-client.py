"""Async HTTP client for the HCP Terraform Cloud REST API v2.

Uses httpx.AsyncClient with:
- Bearer token auth
- application/vnd.api+json content type (JSON:API)
- Exponential backoff on HTTP 429 (rate-limit)
- Centralised error mapping (4xx/5xx → TFCAPIError)
"""
from __future__ import annotations

import asyncio
import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load sibling tfc-models without __init__.py import
# ---------------------------------------------------------------------------

def _load_models():
    alias = "backend.core.tfc_models"
    if alias in _sys.modules:
        return _sys.modules[alias]
    path = _P(__file__).resolve().parent / "tfc-models.py"
    spec = _ilu.spec_from_file_location(alias, path)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TFCAPIError(Exception):
    """Raised when TFC API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"TFC API {status_code}: {message}")


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

_MAX_RETRIES = 4
_BACKOFF_BASE = 1.0  # seconds


async def _with_backoff(coro_factory, *, max_retries: int = _MAX_RETRIES):
    """Call coro_factory() with exponential backoff on HTTP 429."""
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except TFCAPIError as exc:
            if exc.status_code != 429 or attempt == max_retries - 1:
                raise
            wait = _BACKOFF_BASE * (2 ** attempt)
            logger.warning("TFC rate-limited (429); retrying in %.1fs", wait)
            await asyncio.sleep(wait)
    raise RuntimeError("Unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# TFCClient
# ---------------------------------------------------------------------------


class TFCClient:
    """Stateless async client for HCP Terraform Cloud API v2."""

    def __init__(self, token: str, base_url: str = "https://app.terraform.io") -> None:
        if not token:
            raise ValueError("TFC API token must not be empty")
        self._base = f"{base_url.rstrip('/')}/api/v2"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.api+json",
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers, timeout=30.0)

    def _url(self, path: str) -> str:
        return f"{self._base}/{path.lstrip('/')}"

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.is_success:
            return
        try:
            errors = resp.json().get("errors", [])
            msg = "; ".join(e.get("detail", e.get("title", "")) for e in errors) or resp.text
        except Exception:
            msg = resp.text
        raise TFCAPIError(resp.status_code, msg)

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async def _call():
            async with self._client() as c:
                resp = await c.get(self._url(path), params=params)
                self._raise_for_status(resp)
                return resp.json()
        return await _with_backoff(_call)

    async def _post(self, path: str, payload: dict) -> Any:
        async def _call():
            async with self._client() as c:
                resp = await c.post(self._url(path), json=payload)
                self._raise_for_status(resp)
                # 204 No Content
                if resp.status_code == 204:
                    return {}
                return resp.json()
        return await _with_backoff(_call)

    async def _patch(self, path: str, payload: dict) -> Any:
        async def _call():
            async with self._client() as c:
                resp = await c.patch(self._url(path), json=payload)
                self._raise_for_status(resp)
                return resp.json()
        return await _with_backoff(_call)

    async def _delete(self, path: str) -> None:
        async def _call():
            async with self._client() as c:
                resp = await c.delete(self._url(path))
                self._raise_for_status(resp)
        await _with_backoff(_call)

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------

    async def list_organizations(self):
        """List all organizations accessible with the configured token."""
        _m = _load_models()
        data = await self._get("organizations")
        return [_m.TFCOrg.from_jsonapi({"data": item}) for item in data.get("data", [])]

    # ------------------------------------------------------------------
    # Workspaces
    # ------------------------------------------------------------------

    async def list_workspaces(self, org: str):
        """List all workspaces in the given organization."""
        _m = _load_models()
        data = await self._get(f"organizations/{org}/workspaces")
        return [
            _m.TFCWorkspace.from_jsonapi({"data": item}, org_name=org)
            for item in data.get("data", [])
        ]

    async def create_workspace(
        self,
        org: str,
        name: str,
        execution_mode: str = "remote",
        auto_apply: bool = False,
    ):
        """Create a new workspace in the given organization."""
        _m = _load_models()
        payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": name,
                    "execution-mode": execution_mode,
                    "auto-apply": auto_apply,
                },
            }
        }
        data = await self._post(f"organizations/{org}/workspaces", payload)
        return _m.TFCWorkspace.from_jsonapi(data, org_name=org)

    async def update_workspace(self, ws_id: str, **kwargs):
        """Update workspace attributes (execution_mode, auto_apply, etc.)."""
        _m = _load_models()
        # Map Python snake_case → TFC kebab-case attribute names
        attr_map = {
            "execution_mode": "execution-mode",
            "auto_apply": "auto-apply",
            "terraform_version": "terraform-version",
            "working_directory": "working-directory",
        }
        attributes = {attr_map.get(k, k): v for k, v in kwargs.items()}
        payload = {"data": {"type": "workspaces", "attributes": attributes}}
        data = await self._patch(f"workspaces/{ws_id}", payload)
        return _m.TFCWorkspace.from_jsonapi(data)

    async def delete_workspace(self, ws_id: str) -> None:
        """Permanently delete a workspace."""
        await self._delete(f"workspaces/{ws_id}")

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    async def list_variables(self, ws_id: str):
        """List all variables for a workspace."""
        _m = _load_models()
        data = await self._get(f"workspaces/{ws_id}/vars")
        return [_m.TFCVariable.from_jsonapi({"data": item}) for item in data.get("data", [])]

    async def create_variable(
        self,
        ws_id: str,
        key: str,
        value: str,
        category: str = "terraform",
        sensitive: bool = False,
        description: str = "",
        hcl: bool = False,
    ):
        """Create a new variable in the given workspace."""
        _m = _load_models()
        payload = {
            "data": {
                "type": "vars",
                "attributes": {
                    "key": key,
                    "value": value,
                    "category": category,
                    "sensitive": sensitive,
                    "description": description,
                    "hcl": hcl,
                },
                "relationships": {
                    "workspace": {
                        "data": {"id": ws_id, "type": "workspaces"}
                    }
                },
            }
        }
        data = await self._post(f"workspaces/{ws_id}/vars", payload)
        return _m.TFCVariable.from_jsonapi(data)

    async def update_variable(self, ws_id: str, var_id: str, value: str, sensitive: bool = False):
        """Update an existing workspace variable's value."""
        _m = _load_models()
        payload = {
            "data": {
                "id": var_id,
                "type": "vars",
                "attributes": {"value": value, "sensitive": sensitive},
            }
        }
        data = await self._patch(f"workspaces/{ws_id}/vars/{var_id}", payload)
        return _m.TFCVariable.from_jsonapi(data)

    async def delete_variable(self, var_id: str) -> None:
        """Delete a workspace variable by its ID."""
        await self._delete(f"vars/{var_id}")

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    async def create_run(self, ws_id: str, message: str = "", auto_apply: bool = False):
        """Queue a new run for the given workspace."""
        _m = _load_models()
        payload = {
            "data": {
                "type": "runs",
                "attributes": {
                    "message": message,
                    "auto-apply": auto_apply,
                },
                "relationships": {
                    "workspace": {
                        "data": {"id": ws_id, "type": "workspaces"}
                    }
                },
            }
        }
        data = await self._post("runs", payload)
        return _m.TFCRun.from_jsonapi(data)

    async def get_run(self, run_id: str):
        """Get the current state of a run."""
        _m = _load_models()
        data = await self._get(f"runs/{run_id}")
        return _m.TFCRun.from_jsonapi(data)

    async def list_runs(self, ws_id: str):
        """List the most recent runs for a workspace (up to 20)."""
        _m = _load_models()
        data = await self._get(f"workspaces/{ws_id}/runs", params={"page[size]": "20"})
        return [_m.TFCRun.from_jsonapi({"data": item}) for item in data.get("data", [])]

    async def apply_run(self, run_id: str, comment: str = "") -> None:
        """Confirm and apply a run that is awaiting confirmation."""
        await self._post(f"runs/{run_id}/actions/apply", {"comment": comment})

    async def discard_run(self, run_id: str, comment: str = "") -> None:
        """Discard a run that is awaiting confirmation."""
        await self._post(f"runs/{run_id}/actions/discard", {"comment": comment})
