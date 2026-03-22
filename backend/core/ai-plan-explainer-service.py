"""AI plan explainer service for structured plan explanation (Phase 9).

Combines deterministic plan-analysis-helpers with Claude streaming to produce
structured explanations: summary, risk assessment, cost impact, security implications.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import anthropic

from backend.core.config import Settings

logger = logging.getLogger(__name__)

_MAX_PLAN_CHARS = 40_000   # truncate very large plan JSON before sending to Claude


def _analysis():
    from backend.core import load_kebab_module
    return load_kebab_module("plan-analysis-helpers.py", "plan_analysis_helpers")


def _ai_helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-agent-helpers.py", "ai_agent_helpers")


def _prompts():
    from backend.core import load_kebab_module
    return load_kebab_module("prompts/plan-explainer-prompt.py", "prompts.plan_explainer_prompt")


class AIPlanExplainerService:
    """Produces structured AI explanations of terraform plan JSON.

    Args:
        config: Application Settings instance.
    """

    def __init__(self, config: Settings) -> None:
        if not config.anthropic_api_key:
            raise ValueError("TERRABOT_ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = config.ai_model
        self._max_tokens = config.ai_max_tokens

    async def explain_plan_streaming(
        self,
        plan_json: dict,
        workspace_context: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a structured plan explanation.

        Strips sensitive values, pre-computes deterministic summary,
        then yields Claude's response token-by-token.
        """
        a = _analysis()
        ai_h = _ai_helpers()
        system = _prompts().get_prompt()

        # Deterministic pre-processing (fast, no AI cost)
        clean_plan = a.strip_sensitive_values(plan_json)
        summary = a.extract_plan_summary(clean_plan)
        risk = a.assess_risk(clean_plan)
        cost = a.estimate_cost_impact(clean_plan)

        # Truncate plan JSON to avoid context overflow
        plan_text = json.dumps(clean_plan, indent=2)
        if len(plan_text) > _MAX_PLAN_CHARS:
            # Keep only resource_changes section for large plans
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
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            ) as stream:
                async for delta in stream.text_stream:
                    yield delta
                final = await stream.get_final_message()
                ai_h.log_usage(logger, "explain_plan_streaming", final.usage)
        except anthropic.APIError as exc:
            logger.error("Claude API error during explain_plan_streaming: %s", exc)
            yield f"Error generating explanation: {exc}"

    async def get_plan_analysis(self, plan_json: dict) -> dict:
        """Return deterministic plan analysis without calling Claude.

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
