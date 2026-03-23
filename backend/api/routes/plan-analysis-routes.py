"""Plan analysis and AI explanation routes (Phase 9).

POST /api/plans/analyze   — deterministic plan analysis (JSON, no AI)
POST /api/plans/explain   — stream AI plan explanation (SSE)
GET  /api/jobs/{job_id}/plan-analysis — analyze plan from a completed plan job
"""
from __future__ import annotations

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["plan-analysis"])


# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

def _load(rel: str, alias: str):
    full = f"backend.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    base = _P(__file__).resolve().parent.parent
    spec = _ilu.spec_from_file_location(full, base / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    return _load("schemas/plan-analysis-schemas.py", "api.schemas.plan_analysis_schemas")


def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _sse_response(generator) -> StreamingResponse:
    async def event_stream():
        async for chunk in generator:
            safe = chunk.replace("\n", " ")
            yield f"data: {safe}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _get_explainer():
    from backend.core import load_kebab_module
    from backend.core.config import get_settings
    from backend.core.llm import get_llm_client
    svc_mod = load_kebab_module("ai-plan-explainer-service.py", "ai_plan_explainer_service")
    cfg = get_settings()
    return svc_mod.AIPlanExplainerService(client=get_llm_client(cfg), max_tokens=cfg.ai_max_tokens)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/plans/analyze")
async def analyze_plan(request: Request):
    """Deterministic plan analysis — instant, no AI call.

    Returns structured summary, risk assessment, and cost impact based
    on rule-based analysis of the plan JSON.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.PlanExplainRequest(**(await request.json()))

    explainer = _get_explainer()
    analysis = await explainer.get_plan_analysis(body.plan_json)

    return schemas.PlanAnalysisResponse(
        summary=schemas.PlanSummaryResponse(**analysis["summary"]),
        risk=schemas.RiskAssessmentResponse(
            level=analysis["risk"]["level"],
            flags=[schemas.RiskFlagResponse(**f) for f in analysis["risk"]["flags"]],
        ),
        cost=schemas.CostImpactResponse(**analysis["cost"]),
    )


@router.post("/api/plans/explain")
async def explain_plan(request: Request):
    """Stream AI-generated structured plan explanation (SSE).

    Combines deterministic risk/cost analysis with Claude narrative explanation.
    Streams token-by-token for progressive UI rendering.
    """
    _require_auth(request)
    schemas = _schemas()
    body = schemas.PlanExplainRequest(**(await request.json()))

    explainer = _get_explainer()
    gen = explainer.explain_plan_streaming(
        plan_json=body.plan_json,
        workspace_context={"workspace_id": body.workspace_id} if body.workspace_id else None,
    )
    return _sse_response(gen)


@router.get("/api/jobs/{job_id}/plan-analysis")
async def get_job_plan_analysis(job_id: str, request: Request):
    """Return deterministic plan analysis for a specific completed plan job.

    Reads plan JSON from the job record and runs analysis without Claude.
    """
    _require_auth(request)

    # Load job to get its plan output
    from backend.db.database import get_session
    from backend.api.services.job_service import JobService
    async with get_session() as session:
        svc = JobService(session)
        job = await svc.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Job has not completed yet")

    # Attempt to parse plan JSON from job output
    import json
    try:
        plan_json = json.loads(job.output or "{}")
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=422, detail="Job output is not valid plan JSON")

    if not plan_json.get("resource_changes"):
        raise HTTPException(status_code=422, detail="No resource_changes in job output")

    explainer = _get_explainer()
    analysis = await explainer.get_plan_analysis(plan_json)
    schemas = _schemas()

    return schemas.PlanAnalysisResponse(
        summary=schemas.PlanSummaryResponse(**analysis["summary"]),
        risk=schemas.RiskAssessmentResponse(
            level=analysis["risk"]["level"],
            flags=[schemas.RiskFlagResponse(**f) for f in analysis["risk"]["flags"]],
        ),
        cost=schemas.CostImpactResponse(**analysis["cost"]),
    )
