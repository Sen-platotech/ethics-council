"""Stage 1 — in-domain review with multi-model cross-validation."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from config.loader import render_prompt, render_string
from config.schema import CouncilConfig, Expert

from .llm_client import BaseLLMClient


def _build_expert_system_prompt(expert: Expert, config: CouncilConfig) -> str:
    """Render the expert's own system_prompt plus the framework preamble."""
    preamble_lines = ["你必须遵循以下通用伦理原则："]
    for p in config.ethical_framework.principles:
        preamble_lines.append(f"- {p.name}：{p.description}")
    preamble_lines.append("")
    preamble_lines.append("通用审查标准：")
    for c in config.ethical_framework.universal_review_criteria:
        preamble_lines.append(f"- {c}")
    preamble = "\n".join(preamble_lines)

    expert_body = render_string(
        expert.system_prompt or "",
        expert=expert,
        config=config,
        ethical_framework=config.ethical_framework,
    )
    return preamble + "\n\n" + expert_body


def _serialize_project(project) -> str:
    if isinstance(project, str):
        return project
    return json.dumps(project, ensure_ascii=False, indent=2)


async def run_cross_validation(
    project_material: Dict[str, Any],
    expert: Expert,
    models: List[str],
    config: CouncilConfig,
    llm: BaseLLMClient,
) -> Dict[str, Any]:
    """Run one expert domain with 2-3 LLMs (attack/defense + optional arbiter)."""
    if not (config.models.min_models_per_domain <= len(models) <= config.models.max_models_per_domain):
        # Clamp to bounds rather than erroring — the engine is defensive.
        models = list(models)[: config.models.max_models_per_domain]
        while len(models) < config.models.min_models_per_domain:
            # Repeat the last model; the stub doesn't care and real providers
            # will give near-deterministic outputs for low temperature.
            models.append(models[-1] if models else config.models.default_review_models[0])

    expert_system = _build_expert_system_prompt(expert, config)
    project_block = _serialize_project(project_material)

    # Step 1: LLM-A first-pass review.
    _, review_user = render_prompt("stage1_review", project_material=project_block)
    review_a = await llm.query(
        model=models[0],
        system_prompt=expert_system,
        user_prompt=review_user,
        temperature=config.models.temperature,
    )
    review_a_json = review_a.parse_json()

    # Step 2: LLM-B cross-check against A's opinion.
    cross_system, cross_user = render_prompt(
        "stage1_cross_check",
        project_material=project_block,
        peer_opinion_json=json.dumps(review_a_json, ensure_ascii=False, indent=2),
    )
    cross_system = expert_system + "\n\n" + cross_system
    cross_b = await llm.query(
        model=models[1],
        system_prompt=cross_system,
        user_prompt=cross_user,
        temperature=config.models.temperature,
    )
    cross_b_json = cross_b.parse_json()

    # Step 3 (optional): LLM-C third opinion.
    cross_c_json = None
    if len(models) >= 3:
        cross_c = await llm.query(
            model=models[2],
            system_prompt=cross_system,
            user_prompt=cross_user,
            temperature=config.models.temperature,
        )
        cross_c_json = cross_c.parse_json()

    # Step 4: domain summary merge.
    summary_system, summary_user = render_prompt(
        "stage1_domain_summary",
        expert_a_review_json=json.dumps(review_a_json, ensure_ascii=False, indent=2),
        expert_b_cross_check_json=json.dumps(cross_b_json, ensure_ascii=False, indent=2),
        expert_c_cross_check_json=(
            json.dumps(cross_c_json, ensure_ascii=False, indent=2) if cross_c_json else None
        ),
    )
    summary = await llm.query(
        # Merge step uses the strongest available model: chairman by default.
        model=config.models.chairman_model,
        system_prompt=summary_system,
        user_prompt=summary_user,
        temperature=config.models.temperature,
    )
    summary_json = summary.parse_json()

    # Always stamp expert_domain with the canonical display name so downstream
    # stages don't rely on the LLM getting the name right.
    if isinstance(summary_json, dict):
        summary_json.setdefault("expert_domain", expert.display_name(config.language))

    return {
        "expert_id": expert.id,
        "expert_name": expert.display_name(config.language),
        "models_used": models,
        "review_a": review_a_json,
        "cross_check_b": cross_b_json,
        "cross_check_c": cross_c_json,
        "summary": summary_json,
    }
