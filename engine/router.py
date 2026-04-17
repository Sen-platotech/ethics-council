"""Stage 0 — smart routing. Selects experts and identifies cross-domain topics."""

from __future__ import annotations

from typing import Any, Dict, List

from config.loader import render_prompt
from config.schema import (
    ContextCluster,
    CouncilConfig,
    CrossDomainTemplate,
    Expert,
    RoutingResult,
)

from .llm_client import BaseLLMClient


def _serialize_project_material(project: Dict[str, Any]) -> str:
    """Dump project dict as a stable readable block for the prompt."""
    import json

    return json.dumps(project, ensure_ascii=False, indent=2)


async def select_experts(
    project_material,
    experts: List[Expert],
    cross_domain_templates: List[CrossDomainTemplate],
    config: CouncilConfig,
    llm: BaseLLMClient,
) -> RoutingResult:
    """Run the Stage 0 routing agent and return a structured routing result.

    project_material can be a dict or a JSON string.

    On top of the LLM output we apply two rule-based safeguards:
      1. Project booleans (involves_human_subjects etc.) auto-include the
         matching expert even if the LLM missed it.
      2. High-risk checklist items matched against the project text get
         surfaced to the caller.
    """
    import json as _json

    # Normalize: accept both dict and str forms.
    if isinstance(project_material, str):
        try:
            project_dict: Dict[str, Any] = _json.loads(project_material)
        except (ValueError, TypeError):
            project_dict = {}
        project_text = project_material
    else:
        project_dict = project_material
        project_text = _serialize_project_material(project_material)

    system, user = render_prompt(
        "stage0_router",
        available_experts=experts,
        cross_domain_templates=cross_domain_templates,
        high_risk_checklist=config.ethical_framework.high_risk_checklist,
        language=config.language,
        project_material=project_text,
    )

    resp = await llm.query(
        model=config.models.router_model,
        system_prompt=system,
        user_prompt=user,
        temperature=config.models.temperature,
    )
    raw = resp.parse_json() or {}

    # --- Normalize LLM output -> RoutingResult ---
    selected_ids = {e["id"] for e in raw.get("experts_selected", []) if isinstance(e, dict)}

    # Rule 1: auto-include by project flags.
    auto_added: List[Dict[str, Any]] = []
    for exp in experts:
        flags = exp.trigger_conditions.project_flags or []
        if any(project_dict.get(flag) for flag in flags) and exp.id not in selected_ids:
            auto_added.append(
                {
                    "id": exp.id,
                    "name": exp.display_name(config.language),
                    "reason": "auto_included_by_project_flag",
                }
            )
            selected_ids.add(exp.id)
    experts_selected = list(raw.get("experts_selected", [])) + auto_added

    # Rule 2: diversity check — ensure legal expert is included if required.
    if config.pipeline.diversity_check.enabled and config.pipeline.diversity_check.require_legal_expert:
        legal_exp = next(
            (e for e in experts if "legal" in (e.id.lower() + " ".join(e.tags)).lower()),
            None,
        )
        if legal_exp and legal_exp.id not in selected_ids:
            experts_selected.append(
                {
                    "id": legal_exp.id,
                    "name": legal_exp.display_name(config.language),
                    "reason": "auto_included_by_diversity_policy",
                }
            )
            selected_ids.add(legal_exp.id)

    # Normalize clusters: keep only clusters whose participants are all selected.
    clusters: List[ContextCluster] = []
    for c in raw.get("context_clusters", []) or []:
        participants = [p for p in (c.get("participants") or []) if p in selected_ids]
        if len(participants) >= 2:
            clusters.append(
                ContextCluster(
                    topic=c.get("topic") or "未命名议题",
                    participants=participants,
                    reason=c.get("reason"),
                )
            )

    high_risk_flags = list(raw.get("high_risk_flags") or [])
    for item in config.ethical_framework.high_risk_checklist:
        # Very coarse substring check — good enough to surface the concern.
        if any(kw in project_text for kw in _key_terms(item)) and item not in high_risk_flags:
            high_risk_flags.append(item)

    risk_level = raw.get("risk_level") or ("high" if high_risk_flags else "standard")

    return RoutingResult(
        experts_selected=experts_selected,
        context_clusters=clusters,
        experts_not_needed=raw.get("experts_not_needed", []) or [],
        high_risk_flags=high_risk_flags,
        risk_level=risk_level,
    )


def _key_terms(item: str) -> List[str]:
    """Split a checklist entry into coarse keywords for substring matching."""
    import re

    # Keep Chinese nouns > 2 chars and English words > 4 chars.
    tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{4,}", item)
    return tokens[:6]
