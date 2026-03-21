"""Policy as Code management routes (Phase 4).

Policies:
  GET    /api/policies                           — list all policies
  POST   /api/policies                           — create policy
  GET    /api/policies/{id}                      — get policy detail
  PUT    /api/policies/{id}                      — update policy
  DELETE /api/policies/{id}                      — delete policy + remove from OPA
  POST   /api/policies/{id}/test                 — test against sample plan JSON

Policy Sets:
  GET    /api/policy-sets                        — list all sets with member counts
  POST   /api/policy-sets                        — create set
  PUT    /api/policy-sets/{id}                   — update set
  DELETE /api/policy-sets/{id}                   — delete set
  POST   /api/policy-sets/{id}/policies/{pid}    — add policy to set
  DELETE /api/policy-sets/{id}/policies/{pid}    — remove policy from set
  POST   /api/policy-sets/{id}/assign            — assign to workspace(s)
  DELETE /api/policy-sets/{id}/assign/{ws_id}    — unassign from workspace

Results:
  GET    /api/jobs/{job_id}/policy-results       — get policy check results for a run
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.db.database import get_session
from backend.db.models import (
    Policy,
    PolicyCheckResult,
    PolicySet,
    PolicySetAssignment,
    PolicySetMember,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["policies"])


# ---------------------------------------------------------------------------
# Lazy-load kebab-case modules
# ---------------------------------------------------------------------------


def _load_core(filename: str, alias: str):
    """Load a kebab-case core module by filename."""
    full = f"backend.core.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    core_dir = _P(__file__).resolve().parent.parent.parent / "core"
    spec = _ilu.spec_from_file_location(full, core_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_schema(filename: str, alias: str):
    """Load a kebab-case schema module by filename."""
    full = f"backend.api.schemas.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    schemas_dir = _P(__file__).resolve().parent.parent / "schemas"
    spec = _ilu.spec_from_file_location(full, schemas_dir / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _evaluator():
    return _load_core("policy-evaluator.py", "policy_evaluator")


def _schemas():
    return _load_schema("policy-schemas.py", "policy_schemas")


# ---------------------------------------------------------------------------
# Policy CRUD
# ---------------------------------------------------------------------------


@router.get("/policies")
async def list_policies() -> list[dict]:
    """Return all policies."""
    async with get_session() as session:
        result = await session.execute(select(Policy).order_by(Policy.name))
        policies = result.scalars().all()
    s = _schemas()
    return [s.PolicyResponse.model_validate(p).model_dump() for p in policies]


@router.post("/policies", status_code=201)
async def create_policy(body: dict) -> dict:
    """Create a new policy and load it into OPA."""
    s = _schemas()
    req = s.PolicyCreateRequest(**body)

    async with get_session() as session:
        # Enforce unique name
        existing = await session.execute(
            select(Policy).where(Policy.name == req.name)
        )
        if existing.scalars().first():
            raise HTTPException(400, f"Policy name '{req.name}' already exists")

        policy = Policy(
            name=req.name,
            description=req.description,
            rego_code=req.rego_code,
            enforcement=req.enforcement,
            created_by="system",
        )
        session.add(policy)
        await session.flush()
        policy_id = policy.id
        rego_code = policy.rego_code
        response = s.PolicyResponse.model_validate(policy).model_dump()

    # Load into OPA (outside session to avoid long-held connection)
    ev = _evaluator()
    await ev.load_policy_to_opa(policy_id, rego_code)
    return response


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str) -> dict:
    """Return policy detail by ID."""
    async with get_session() as session:
        policy = await session.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(404, "Policy not found")
    s = _schemas()
    return s.PolicyResponse.model_validate(policy).model_dump()


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, body: dict) -> dict:
    """Update policy fields. Reloads into OPA if rego_code changed."""
    s = _schemas()
    req = s.PolicyUpdateRequest(**body)

    async with get_session() as session:
        policy = await session.get(Policy, policy_id)
        if policy is None:
            raise HTTPException(404, "Policy not found")

        rego_changed = False
        if req.name is not None:
            policy.name = req.name
        if req.description is not None:
            policy.description = req.description
        if req.rego_code is not None and req.rego_code != policy.rego_code:
            policy.rego_code = req.rego_code
            rego_changed = True
        if req.enforcement is not None:
            policy.enforcement = req.enforcement

        await session.flush()
        pid = policy.id
        rego_code = policy.rego_code
        response = s.PolicyResponse.model_validate(policy).model_dump()

    if rego_changed:
        ev = _evaluator()
        await ev.load_policy_to_opa(pid, rego_code)

    return response


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(policy_id: str) -> None:
    """Delete policy from DB and remove from OPA."""
    async with get_session() as session:
        policy = await session.get(Policy, policy_id)
        if policy is None:
            raise HTTPException(404, "Policy not found")
        await session.delete(policy)

    ev = _evaluator()
    await ev.remove_policy_from_opa(policy_id)


@router.post("/policies/{policy_id}/test")
async def test_policy(policy_id: str, body: dict) -> dict:
    """Test policy against a sample plan JSON.

    Loads policy to OPA under a temp ID, evaluates, cleans up.
    """
    s = _schemas()
    req = s.PolicyTestRequest(**body)

    async with get_session() as session:
        policy = await session.get(Policy, policy_id)
        if policy is None:
            raise HTTPException(404, "Policy not found")
        name = policy.name
        rego_code = policy.rego_code

    ev = _evaluator()

    # Use a temp OPA ID so we don't collide with the live policy
    temp_id = f"__test__{policy_id}"
    await ev.load_policy_to_opa(temp_id, rego_code)

    try:
        opa_path = f"terrabot/policy/{name.replace('-', '_').replace(' ', '_')}"
        input_doc = {
            "plan": req.plan_json,
            "workspace": {"name": "test", "provider": "test", "env": "test"},
            "run": {"job_id": "test", "trigger": "manual", "user": "system"},
        }
        # Access private helper via module reference
        opa_result = await ev._query_opa_policy(opa_path, input_doc)
        violations = opa_result.get("violations", [])
        warnings = opa_result.get("warnings", [])
        if isinstance(violations, set):
            violations = list(violations)
        if isinstance(warnings, set):
            warnings = list(warnings)
    finally:
        await ev.remove_policy_from_opa(temp_id)

    resp = s.PolicyTestResponse(
        violations=violations,
        warnings=warnings,
        passed=len(violations) == 0,
    )
    return resp.model_dump()


# ---------------------------------------------------------------------------
# Policy Sets CRUD
# ---------------------------------------------------------------------------


@router.get("/policy-sets")
async def list_policy_sets() -> list[dict]:
    """Return all policy sets with member counts."""
    async with get_session() as session:
        result = await session.execute(
            select(PolicySet).order_by(PolicySet.name)
        )
        sets = result.scalars().all()

    s = _schemas()
    out = []
    for ps in sets:
        out.append(
            s.PolicySetResponse(
                id=ps.id,
                name=ps.name,
                description=ps.description,
                scope=ps.scope,
                policy_count=len(ps.members),
                created_at=ps.created_at,
            ).model_dump()
        )
    return out


@router.post("/policy-sets", status_code=201)
async def create_policy_set(body: dict) -> dict:
    """Create a new policy set."""
    s = _schemas()
    req = s.PolicySetCreateRequest(**body)

    async with get_session() as session:
        existing = await session.execute(
            select(PolicySet).where(PolicySet.name == req.name)
        )
        if existing.scalars().first():
            raise HTTPException(400, f"Policy set name '{req.name}' already exists")

        ps = PolicySet(
            name=req.name,
            description=req.description,
            scope=req.scope,
        )
        session.add(ps)
        await session.flush()

        response = s.PolicySetResponse(
            id=ps.id,
            name=ps.name,
            description=ps.description,
            scope=ps.scope,
            policy_count=0,
            created_at=ps.created_at,
        ).model_dump()

    return response


@router.put("/policy-sets/{set_id}")
async def update_policy_set(set_id: str, body: dict) -> dict:
    """Update policy set name, description, or scope."""
    async with get_session() as session:
        ps = await session.get(PolicySet, set_id)
        if ps is None:
            raise HTTPException(404, "Policy set not found")

        if "name" in body:
            ps.name = body["name"]
        if "description" in body:
            ps.description = body["description"]
        if "scope" in body:
            ps.scope = body["scope"]

        await session.flush()
        s = _schemas()
        response = s.PolicySetResponse(
            id=ps.id,
            name=ps.name,
            description=ps.description,
            scope=ps.scope,
            policy_count=len(ps.members),
            created_at=ps.created_at,
        ).model_dump()

    return response


@router.delete("/policy-sets/{set_id}", status_code=204)
async def delete_policy_set(set_id: str) -> None:
    """Delete a policy set (cascade removes members and assignments)."""
    async with get_session() as session:
        ps = await session.get(PolicySet, set_id)
        if ps is None:
            raise HTTPException(404, "Policy set not found")
        await session.delete(ps)


@router.post("/policy-sets/{set_id}/policies/{policy_id}", status_code=201)
async def add_policy_to_set(set_id: str, policy_id: str) -> dict:
    """Add a policy to a policy set."""
    async with get_session() as session:
        ps = await session.get(PolicySet, set_id)
        if ps is None:
            raise HTTPException(404, "Policy set not found")

        policy = await session.get(Policy, policy_id)
        if policy is None:
            raise HTTPException(404, "Policy not found")

        # Check not already a member
        existing = await session.execute(
            select(PolicySetMember).where(
                PolicySetMember.policy_set_id == set_id,
                PolicySetMember.policy_id == policy_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(409, "Policy already in set")

        member = PolicySetMember(policy_set_id=set_id, policy_id=policy_id)
        session.add(member)

    return {"policy_set_id": set_id, "policy_id": policy_id}


@router.delete("/policy-sets/{set_id}/policies/{policy_id}", status_code=204)
async def remove_policy_from_set(set_id: str, policy_id: str) -> None:
    """Remove a policy from a policy set."""
    async with get_session() as session:
        result = await session.execute(
            select(PolicySetMember).where(
                PolicySetMember.policy_set_id == set_id,
                PolicySetMember.policy_id == policy_id,
            )
        )
        member = result.scalars().first()
        if member is None:
            raise HTTPException(404, "Policy not in set")
        await session.delete(member)


@router.post("/policy-sets/{set_id}/assign", status_code=201)
async def assign_policy_set(set_id: str, body: dict) -> dict:
    """Assign a policy set to one or more workspaces."""
    s = _schemas()
    req = s.PolicySetAssignRequest(**body)

    async with get_session() as session:
        ps = await session.get(PolicySet, set_id)
        if ps is None:
            raise HTTPException(404, "Policy set not found")

        assigned: list[str] = []
        for ws_id in req.workspace_ids:
            # Skip duplicates silently
            existing = await session.execute(
                select(PolicySetAssignment).where(
                    PolicySetAssignment.policy_set_id == set_id,
                    PolicySetAssignment.workspace_id == ws_id,
                )
            )
            if existing.scalars().first():
                continue
            assignment = PolicySetAssignment(
                policy_set_id=set_id,
                workspace_id=ws_id,
            )
            session.add(assignment)
            assigned.append(ws_id)

    return {"policy_set_id": set_id, "assigned_workspace_ids": assigned}


@router.delete("/policy-sets/{set_id}/assign/{workspace_id}", status_code=204)
async def unassign_policy_set(set_id: str, workspace_id: str) -> None:
    """Remove a policy set assignment from a workspace."""
    async with get_session() as session:
        result = await session.execute(
            select(PolicySetAssignment).where(
                PolicySetAssignment.policy_set_id == set_id,
                PolicySetAssignment.workspace_id == workspace_id,
            )
        )
        assignment = result.scalars().first()
        if assignment is None:
            raise HTTPException(404, "Assignment not found")
        await session.delete(assignment)


# ---------------------------------------------------------------------------
# Policy Check Results
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/policy-results")
async def get_job_policy_results(job_id: str) -> list[dict]:
    """Return all policy check results for a given job/run."""
    async with get_session() as session:
        result = await session.execute(
            select(PolicyCheckResult)
            .where(PolicyCheckResult.job_id == job_id)
            .order_by(PolicyCheckResult.evaluated_at)
        )
        records = result.scalars().all()

    s = _schemas()
    out = []
    for r in records:
        violations = json.loads(r.violations_json) if r.violations_json else []
        out.append(
            s.PolicyCheckResultResponse(
                id=r.id,
                policy_name=r.policy_name,
                enforcement=r.enforcement,
                passed=r.passed,
                violations=violations,
                evaluated_at=r.evaluated_at,
            ).model_dump()
        )
    return out
