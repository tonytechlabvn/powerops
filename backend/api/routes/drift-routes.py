"""Drift detection routes.

POST /api/drift/check       — run a drift check for a workspace
GET  /api/drift/history     — retrieve past drift reports
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/drift", tags=["drift"])


class DriftCheckRequest(BaseModel):
    workspace: str
    workspace_dir: str


class DriftResourceItem(BaseModel):
    address: str
    type: str
    name: str
    actions: list[str]


class DriftReportResponse(BaseModel):
    workspace: str
    timestamp: str
    has_drift: bool
    drifted_resources: list[DriftResourceItem] = []
    error: str = ""


def _load_detector():
    import importlib.util as ilu
    import sys
    from pathlib import Path

    alias = "backend.core.drift_detector"
    if alias in sys.modules:
        return sys.modules[alias]
    core_dir = Path(__file__).parent.parent.parent / "core"
    spec = ilu.spec_from_file_location(alias, core_dir / "drift-detector.py")
    mod = ilu.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@router.post("/check", response_model=DriftReportResponse)
async def check_drift(body: DriftCheckRequest) -> DriftReportResponse:
    """Run terraform plan in refresh-only mode to detect infrastructure drift."""
    mod = _load_detector()
    detector = mod.DriftDetector()
    report = await detector.check_drift(
        workspace=body.workspace,
        workspace_dir=body.workspace_dir,
    )
    return DriftReportResponse(
        workspace=report.workspace,
        timestamp=report.timestamp,
        has_drift=report.has_drift,
        drifted_resources=[
            DriftResourceItem(
                address=r.get("address", ""),
                type=r.get("type", ""),
                name=r.get("name", ""),
                actions=r.get("actions", []),
            )
            for r in report.drifted_resources
        ],
        error=report.error,
    )


@router.get("/history", response_model=list[DriftReportResponse])
async def drift_history(
    workspace: str = Query(..., description="Workspace name"),
    limit: int = Query(20, ge=1, le=100),
) -> list[DriftReportResponse]:
    """Return past drift check results for a workspace."""
    mod = _load_detector()
    detector = mod.DriftDetector()
    history = await detector.get_drift_history(workspace=workspace, limit=limit)
    return [
        DriftReportResponse(
            workspace=r.workspace,
            timestamp=r.timestamp,
            has_drift=r.has_drift,
            drifted_resources=[
                DriftResourceItem(
                    address=d.get("address", ""),
                    type=d.get("type", ""),
                    name=d.get("name", ""),
                    actions=d.get("actions", []),
                )
                for d in r.drifted_resources
            ],
            error=r.error,
        )
        for r in history
    ]
