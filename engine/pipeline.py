"""Main pipeline orchestration — wires Stage 0 → 1 → 2 → 3."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from config.schema import (
    ContextCluster,
    CouncilConfig,
    Expert,
    Preset,
    RoutingResult,
)

from . import chairman, context_discussion, domain_review, router
from .llm_client import BaseLLMClient, make_llm_client


UserConfirmCallback = Callable[[RoutingResult], Optional[Dict[str, Any]]]


async def run_ethics_review(
    project_material: Dict[str, Any],
    config: CouncilConfig,
    preset: Preset,
    *,
    llm: Optional[BaseLLMClient] = None,
    user_confirm: Optional[UserConfirmCallback] = None,
    expert_model_overrides: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Run the full four-stage ethics review.

    Args:
        project_material: Structured project application dict.
        config: Loaded council configuration.
        preset: Loaded preset (experts + cross-domain templates).
        llm: Optional LLM client. Defaults to a provider built from
            config.models.api_provider (stub by default).
        user_confirm: Optional callback invoked after Stage 0 with the routing
            result. It may return a dict with keys {"experts", "clusters"} to
            override the LLM's selection. Return None to accept the routing
            as-is. In CLI / batch runs leave this as None.
        expert_model_overrides: Map expert_id -> list[model_name] to override
            the default review models per domain.

    Returns:
        The final Stage 3 JSON opinion, plus an embedded _deliberation_log
        if config.output.include_deliberation_log is True.
    """
    llm = llm or make_llm_client(
        config.models.api_provider,
        temperature=config.models.temperature,
        timeout=config.models.request_timeout,
    )

    # -------- Stage 0: routing --------
    if config.pipeline.enable_stage0_routing:
        routing = await router.select_experts(
            project_material=project_material,
            experts=preset.experts,
            cross_domain_templates=preset.cross_domain_templates,
            config=config,
            llm=llm,
        )
    else:
        routing = RoutingResult(
            experts_selected=[
                {"id": e.id, "name": e.display_name(config.language), "reason": "manual_mode_all_selected"}
                for e in preset.experts
            ],
            context_clusters=[
                ContextCluster(topic=t.topic, participants=t.participants, reason="template")
                for t in preset.cross_domain_templates
            ],
        )

    # Optional human-in-the-loop confirmation.
    if user_confirm is not None:
        override = user_confirm(routing)
        if override:
            if "experts" in override:
                routing.experts_selected = override["experts"]
            if "clusters" in override:
                routing.context_clusters = [
                    c if isinstance(c, ContextCluster) else ContextCluster(**c)
                    for c in override["clusters"]
                ]

    # Resolve selected expert IDs → Expert objects.
    selected_ids = [e["id"] for e in routing.experts_selected]
    selected_experts: List[Expert] = [
        exp for exp in preset.experts if exp.id in selected_ids
    ]

    # -------- Stage 1: domain reviews --------
    domain_results: List[Dict[str, Any]] = []
    for expert in selected_experts:
        models = (expert_model_overrides or {}).get(
            expert.id, config.models.default_review_models
        )
        result = await domain_review.run_cross_validation(
            project_material=project_material,
            expert=expert,
            models=models,
            config=config,
            llm=llm,
        )
        domain_results.append(result)

    # -------- Stage 2: context-clustered discussions --------
    context_discussions: List[Dict[str, Any]] = []
    if config.pipeline.enable_cross_domain_discussion and routing.context_clusters:
        summary_by_id = {r["expert_id"]: r["summary"] for r in domain_results}
        for cluster in routing.context_clusters:
            participant_experts = [
                e for e in selected_experts if e.id in cluster.participants
            ]
            if len(participant_experts) < 2:
                # Cluster collapsed to <2 participants — skip.
                continue
            discussion = await context_discussion.run_discussion(
                cluster=cluster,
                participant_experts=participant_experts,
                domain_summaries=summary_by_id,
                config=config,
                llm=llm,
            )
            context_discussions.append(discussion)

    # -------- Stage 3: chairman synthesis --------
    final = await chairman.synthesize(
        project_material=project_material,
        domain_results=domain_results,
        context_discussions=context_discussions,
        risk_level=routing.risk_level,
        config=config,
        llm=llm,
    )

    # Attach routing at top-level for traceability.
    if isinstance(final, dict):
        final["_routing"] = routing.model_dump()
    return final
