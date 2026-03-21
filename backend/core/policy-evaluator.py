"""OPA policy evaluation orchestration for TerraBot (Phase 4).

Responsibilities:
- Load/remove Rego policies to/from the OPA sidecar via REST
- Evaluate all applicable policies against a Terraform plan JSON
- Store PolicyCheckResult records in DB
- Determine can-apply status based on enforcement levels
- Startup sync and starter policy seeding
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
from sqlalchemy import select

from backend.core.config import get_settings
from backend.db.database import get_session
from backend.db.models import (
    Policy,
    PolicyCheckResult,
    PolicySet,
    PolicySetAssignment,
    PolicySetMember,
    Workspace,
)

logger = logging.getLogger(__name__)

# Policies directory (relative to project root, resolved at runtime)
_POLICIES_DIR = Path(__file__).resolve().parent.parent.parent / "policies"


# ---------------------------------------------------------------------------
# OPA REST helpers
# ---------------------------------------------------------------------------


def _opa_base() -> str:
    return get_settings().opa_url.rstrip("/")


async def load_policy_to_opa(policy_id: str, rego_code: str) -> bool:
    """PUT Rego source to OPA at /v1/policies/{policy_id}. Returns True on success."""
    url = f"{_opa_base()}/v1/policies/{policy_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                url,
                content=rego_code.encode(),
                headers={"Content-Type": "text/plain"},
            )
        if resp.status_code in (200, 201):
            logger.debug("Loaded policy %s to OPA", policy_id)
            return True
        logger.warning("OPA PUT %s → %s: %s", url, resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("Failed to load policy %s to OPA: %s", policy_id, exc)
        return False


async def remove_policy_from_opa(policy_id: str) -> bool:
    """DELETE policy from OPA. Returns True on success."""
    url = f"{_opa_base()}/v1/policies/{policy_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url)
        if resp.status_code in (200, 204, 404):
            logger.debug("Removed policy %s from OPA", policy_id)
            return True
        logger.warning("OPA DELETE %s → %s", url, resp.status_code)
        return False
    except Exception as exc:
        logger.error("Failed to remove policy %s from OPA: %s", policy_id, exc)
        return False


async def _query_opa_policy(policy_name: str, input_doc: dict) -> dict:
    """POST input to OPA data endpoint and return parsed result."""
    # OPA path: terrabot/policy/{name} (dots → slashes)
    opa_path = policy_name.replace(".", "/")
    url = f"{_opa_base()}/v1/data/{opa_path}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"input": input_doc})
        if resp.status_code == 200:
            return resp.json().get("result", {}) or {}
        logger.warning("OPA query %s → %s: %s", url, resp.status_code, resp.text[:200])
        return {}
    except Exception as exc:
        logger.error("OPA query failed for %s: %s", policy_name, exc)
        return {}


# ---------------------------------------------------------------------------
# Plan evaluation
# ---------------------------------------------------------------------------


def _build_input(plan_json: dict, workspace: Workspace, job_id: str) -> dict:
    """Construct the OPA input document from plan + workspace context."""
    return {
        "plan": plan_json,
        "workspace": {
            "name": workspace.name,
            "provider": workspace.provider,
            "env": workspace.environment,
        },
        "run": {
            "job_id": job_id,
            "trigger": "manual",
            "user": "system",
        },
    }


async def evaluate_plan(
    job_id: str,
    workspace_id: str,
    plan_json: dict,
) -> list[dict]:
    """Evaluate all applicable policies for a workspace against plan_json.

    Steps:
    1. Fetch assigned policy sets (workspace-specific + org-wide)
    2. Collect all policies from those sets
    3. Ensure each policy is loaded in OPA
    4. Query OPA for violations/warnings per policy
    5. Persist PolicyCheckResult records
    6. Return list of result dicts

    Returns:
        List of {policy_id, policy_name, enforcement, passed, violations, warnings}
    """
    if not get_settings().policy_check_enabled:
        logger.info("Policy checks disabled, skipping evaluation for job %s", job_id)
        return []

    async with get_session() as session:
        # Fetch workspace for context
        ws = await session.get(Workspace, workspace_id)
        if ws is None:
            logger.warning("Workspace %s not found, skipping policy eval", workspace_id)
            return []

        # Fetch policy set assignments: workspace-specific OR org-wide (NULL workspace_id)
        stmt = select(PolicySetAssignment).where(
            (PolicySetAssignment.workspace_id == workspace_id)
            | (PolicySetAssignment.workspace_id.is_(None))
        )
        result = await session.execute(stmt)
        assignments = result.scalars().all()

        if not assignments:
            logger.info("No policy sets assigned to workspace %s", workspace_id)
            return []

        policy_set_ids = list({a.policy_set_id for a in assignments})

        # Fetch all policy IDs in those sets
        stmt2 = select(PolicySetMember).where(
            PolicySetMember.policy_set_id.in_(policy_set_ids)
        )
        result2 = await session.execute(stmt2)
        members = result2.scalars().all()

        if not members:
            logger.info("No policies in assigned sets for workspace %s", workspace_id)
            return []

        policy_ids = list({m.policy_id for m in members})

        # Fetch Policy records
        stmt3 = select(Policy).where(Policy.id.in_(policy_ids))
        result3 = await session.execute(stmt3)
        policies = result3.scalars().all()

        input_doc = _build_input(plan_json, ws, job_id)
        check_results: list[dict] = []

        for policy in policies:
            # Ensure policy loaded in OPA
            await load_policy_to_opa(policy.id, policy.rego_code)

            # Derive OPA query path from policy name: spaces/dots → underscores
            opa_policy_name = f"terrabot/policy/{policy.name.replace('-', '_').replace(' ', '_')}"
            opa_result = await _query_opa_policy(opa_policy_name, input_doc)

            violations = opa_result.get("violations", [])
            warnings = opa_result.get("warnings", [])
            # Normalise to list
            if isinstance(violations, set):
                violations = list(violations)
            if isinstance(warnings, set):
                warnings = list(warnings)

            passed = len(violations) == 0

            # Persist result
            pcr = PolicyCheckResult(
                job_id=job_id,
                policy_id=policy.id,
                policy_name=policy.name,
                enforcement=policy.enforcement,
                passed=passed,
                violations_json=json.dumps(violations),
            )
            session.add(pcr)

            check_results.append({
                "policy_id": policy.id,
                "policy_name": policy.name,
                "enforcement": policy.enforcement,
                "passed": passed,
                "violations": violations,
                "warnings": warnings,
            })

        await session.commit()

    logger.info(
        "Policy evaluation for job %s: %d policies checked, %d passed",
        job_id,
        len(check_results),
        sum(1 for r in check_results if r["passed"]),
    )
    return check_results


# ---------------------------------------------------------------------------
# Apply gate
# ---------------------------------------------------------------------------


async def check_can_apply(job_id: str) -> tuple[bool, str]:
    """Determine if a job is allowed to apply based on policy results.

    Rules:
    - hard-mandatory violation → blocked unconditionally
    - soft-mandatory violation + no override → blocked (requires admin override)
    - soft-mandatory violation + override approved → allowed
    - advisory violations → always allowed (warnings only)
    - no violations → allowed

    Returns:
        (can_apply: bool, reason: str)
    """
    async with get_session() as session:
        stmt = select(PolicyCheckResult).where(PolicyCheckResult.job_id == job_id)
        result = await session.execute(stmt)
        results = result.scalars().all()

        if not results:
            return True, ""

        # Check for policy override on the approval
        from backend.db.models import Approval
        stmt_ap = select(Approval).where(Approval.job_id == job_id)
        ap_result = await session.execute(stmt_ap)
        approval = ap_result.scalars().first()
        has_override = approval is not None and approval.policy_override

        failed_hard: list[str] = []
        failed_soft: list[str] = []

        for r in results:
            if r.passed:
                continue
            if r.enforcement == "hard-mandatory":
                failed_hard.append(r.policy_name)
            elif r.enforcement == "soft-mandatory":
                failed_soft.append(r.policy_name)
            # advisory failures do not block

        if failed_hard:
            names = ", ".join(failed_hard)
            return False, f"blocked by policy: {names}"

        if failed_soft:
            if has_override:
                logger.info("Soft-mandatory policies overridden for job %s", job_id)
                return True, ""
            names = ", ".join(failed_soft)
            return False, f"requires admin override for: {names}"

    return True, ""


# ---------------------------------------------------------------------------
# Startup helpers
# ---------------------------------------------------------------------------


async def sync_policies_to_opa() -> int:
    """Load ALL policies from DB into OPA. Called at startup. Returns count loaded."""
    count = 0
    try:
        async with get_session() as session:
            result = await session.execute(select(Policy))
            policies = result.scalars().all()

        for policy in policies:
            ok = await load_policy_to_opa(policy.id, policy.rego_code)
            if ok:
                count += 1

        logger.info("Synced %d policies to OPA", count)
    except Exception as exc:
        logger.error("sync_policies_to_opa failed: %s", exc)
    return count


async def seed_starter_policies() -> int:
    """If policies table empty, seed from .rego files in policies/ directory.

    Creates each file as an advisory Policy record, then creates a
    'Starter' PolicySet containing all of them.

    Returns:
        Number of policies seeded (0 if table was not empty).
    """
    if not _POLICIES_DIR.is_dir():
        logger.info("policies/ directory not found, skipping seed")
        return 0

    rego_files = list(_POLICIES_DIR.glob("*.rego"))
    if not rego_files:
        logger.info("No .rego files found in policies/, skipping seed")
        return 0

    async with get_session() as session:
        # Check if any policies exist
        result = await session.execute(select(Policy).limit(1))
        if result.scalars().first() is not None:
            logger.debug("Policies table not empty, skipping seed")
            return 0

        seeded_ids: list[str] = []
        for rego_path in rego_files:
            name = rego_path.stem.replace("_", "-")  # kebab-case name from filename
            try:
                rego_code = rego_path.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Could not read %s: %s", rego_path, exc)
                continue

            policy = Policy(
                name=name,
                description=f"Starter policy from {rego_path.name}",
                rego_code=rego_code,
                enforcement="advisory",
                created_by="system",
            )
            session.add(policy)
            await session.flush()  # get generated ID
            seeded_ids.append(policy.id)
            logger.info("Seeded starter policy: %s", name)

        if not seeded_ids:
            return 0

        # Create Starter PolicySet
        starter_set = PolicySet(
            name="Starter",
            description="Built-in starter policies seeded from policies/ directory",
            scope="global",
        )
        session.add(starter_set)
        await session.flush()

        for pid in seeded_ids:
            member = PolicySetMember(
                policy_set_id=starter_set.id,
                policy_id=pid,
            )
            session.add(member)

        await session.commit()

    logger.info("Seeded %d starter policies into 'Starter' PolicySet", len(seeded_ids))
    return len(seeded_ids)
