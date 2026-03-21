"""Import wizard routes.

POST /api/import/config — generate HCL stub for a resource
POST /api/import/run    — run terraform import for a single resource
POST /api/import/bulk   — run terraform import for multiple resources
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportConfigRequest(BaseModel):
    resource_type: str
    resource_id: str
    tf_name: str


class ImportConfigResponse(BaseModel):
    hcl: str


class ImportRunRequest(BaseModel):
    resource_type: str
    resource_id: str
    tf_address: str
    workspace_dir: str


class ImportRunResponse(BaseModel):
    success: bool
    address: str
    resource_id: str
    output: str = ""
    error: str = ""


class BulkImportRequest(BaseModel):
    workspace_dir: str
    mapping: list[dict]  # [{resource_type, resource_id, tf_address}]


def _load_wizard():
    import importlib.util as ilu
    import sys
    from pathlib import Path

    alias = "backend.core.import_wizard"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "import-wizard.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _wizard():
    mod = _load_wizard()
    return mod.ImportWizard()


@router.post("/config", response_model=ImportConfigResponse)
async def generate_config(body: ImportConfigRequest) -> ImportConfigResponse:
    """Generate a minimal HCL resource stub for the given resource type."""
    hcl = await _wizard().generate_import_config(
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        tf_name=body.tf_name,
    )
    return ImportConfigResponse(hcl=hcl)


@router.post("/run", response_model=ImportRunResponse)
async def run_import(body: ImportRunRequest) -> ImportRunResponse:
    """Execute terraform import for a single resource."""
    result = await _wizard().run_import(
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        tf_address=body.tf_address,
        workspace_dir=body.workspace_dir,
    )
    return ImportRunResponse(**result)


@router.post("/bulk", response_model=list[ImportRunResponse])
async def bulk_import(body: BulkImportRequest) -> list[ImportRunResponse]:
    """Execute terraform import for multiple resources in sequence."""
    results = await _wizard().bulk_import(
        mapping=body.mapping,
        workspace_dir=body.workspace_dir,
    )
    return [ImportRunResponse(**r) for r in results]
