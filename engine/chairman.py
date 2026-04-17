"""Stage 3 — Chairman synthesis. Produces the final review opinion."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List

from config.loader import render_prompt
from config.schema import CouncilConfig

from .llm_client import BaseLLMClient


async def synthesize(
    project_material,
    domain_results: List[Dict[str, Any]],
    context_discussions: List[Dict[str, Any]],
    risk_level: str,
    config: CouncilConfig,
    llm: BaseLLMClient,
) -> Dict[str, Any]:
    """Call the chairman LLM and return the final ethics-review JSON."""
    import json as _json

    domain_summaries = [r["summary"] for r in domain_results if r.get("summary")]

    # Accept both dict and str forms.
    if isinstance(project_material, str):
        try:
            _pm = _json.loads(project_material)
        except (ValueError, TypeError):
            _pm = {}
    else:
        _pm = project_material
    project_name = _pm.get("project_title") or _pm.get("project_name") or "未命名项目"
    review_date = _dt.date.today().isoformat()

    system, user = render_prompt(
        "stage3_chairman",
        project_name=project_name,
        review_date=review_date,
        risk_level=risk_level,
        domain_summaries=domain_summaries,
        context_discussions=context_discussions,
    )

    resp = await llm.query(
        model=config.models.chairman_model,
        system_prompt=system,
        user_prompt=user,
        temperature=config.models.temperature,
    )
    final = resp.parse_json() or {}

    # Stamp key fields in case the LLM omitted them.
    if isinstance(final, dict):
        final.setdefault("project_name", project_name)
        final.setdefault("review_date", review_date)
        final.setdefault("risk_level", risk_level)
        if config.output.include_deliberation_log:
            final["_deliberation_log"] = {
                "domain_results": domain_results,
                "context_discussions": context_discussions,
            }
    return final
