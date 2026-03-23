"""AI plan explainer service for structured plan explanation (Phase 9).

Combines deterministic plan-analysis-helpers with LLM streaming to produce
structured explanations: summary, risk assessment, cost impact, security implications.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from backend.core.llm import LLMError

logger = logging.getLogger(__name__)

_MAX_PLAN_CHARS = 40_000   # truncate very large plan JSON before sending to LLM


def _analysis():
    from backend.core import load_kebab_module
    return load_kebab_module("plan-analysis-helpers.py", "plan_analysis_helpers")


def _prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/plan-explainer-prompt.py", "prompts.plan_explainer_prompt")


class AIPlanExplainerService:
    """Produces structured AI explanations of terraform plan JSON.

    Args:
        client: An LLMClient instance.
        max_tokens: Max tokens for completions.
    """

    def __init__(self, client, max_tokens: int = 4096) -> None:
        self._client = client
        self._max_tokens = max_tokens

    async def explain_plan_streaming(
        self,
        plan_json: dict,
        workspace_context: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a structured plan explanation.

        Strips sensitive values, pre-computes deterministic summary,
        then yields LLM response token-by-token.
        """
        a = _analysis()
        system = _prompts().get_prompt()

        # Deterministic pre-processing (fast, no AI cost)
        clean_plan = a.strip_sensitive_values(plan_json)
        summary = a.extract_plan_summary(clean_plan)
        risk = a.assess_risk(clean_plan)
        cost = a.estimate_cost_impact(clean_plan)

        # Truncate plan JSON to avoid context overflow
        plan_text = json.dumps(clean_plan, indent=2)
        if len(plan_text) > _MAX_PLAN_CHARS:
            reduced = {"resource_changes": clean_plan.get("resource_changes", [])}
            plan_text = json.dumps(reduced, indent=2)[:_MAX_PLAN_CHARS]
            plan_text += "\n# ... plan truncated due to size ..."

        user_msg = (
            f"Explain this Terraform plan. "
            f"Pre-computed stats: {summary.creates} creates, {summary.updates} updates, "
            f"{summary.destroys} destroys, {summary.replacements} replacements. "
            f"Deterministic risk level: {risk.level}. "
            f"Cost direction: {cost.direction} ({cost.estimate}).\n\n"
            f"Plan JSON:\n{plan_text}"
        )

        try:
            async for delta in self._client.stream(
                system=system,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=self._max_tokens,
            ):
                yield delta
        except LLMError as exc:
            logger.error("LLM error during explain_plan_streaming: %s", exc)
            yield f"Error generating explanation: {exc}"

    async def get_plan_analysis(self, plan_json: dict) -> dict:
        """Return deterministic plan analysis without calling the LLM.

        Used for fast risk/cost badges that appear before the AI explanation loads.
        Returns serialisable dict with summary, risk, cost fields.
        """
        a = _analysis()
        clean_plan = a.strip_sensitive_values(plan_json)
        summary = a.extract_plan_summary(clean_plan)
        risk = a.assess_risk(clean_plan)
        cost = a.estimate_cost_impact(clean_plan)

        return {
            "summary": {
                "total_changes": summary.total_changes,
                "creates": summary.creates,
                "updates": summary.updates,
                "destroys": summary.destroys,
                "replacements": summary.replacements,
                "resource_types": summary.resource_types,
                "affected_modules": summary.affected_modules,
            },
            "risk": {
                "level": risk.level,
                "flags": [
                    {"type": f.type, "resource": f.resource, "reason": f.reason}
                    for f in risk.flags
                ],
            },
            "cost": {
                "direction": cost.direction,
                "estimate": cost.estimate,
            },
        }
