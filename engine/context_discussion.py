"""Stage 2 — context-clustered cross-domain discussion."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from config.loader import render_prompt, render_string
from config.schema import ContextCluster, CouncilConfig, Expert

from .domain_review import _build_expert_system_prompt
from .llm_client import BaseLLMClient
from .token_optimizer import check_consensus, extract_summary_for_relay


async def run_discussion(
    cluster: ContextCluster,
    participant_experts: List[Expert],
    domain_summaries: Dict[str, Dict[str, Any]],
    config: CouncilConfig,
    llm: BaseLLMClient,
) -> Dict[str, Any]:
    """Run one context cluster's cross-domain discussion.

    `domain_summaries` maps expert_id -> Stage 1 merged summary dict.
    Returns a dict with per-participant outputs + consensus flag.
    """
    # Summary relay: keep only the distilled payload.
    relayed_summaries = [
        extract_summary_for_relay(domain_summaries[eid], max_tokens=config.pipeline.summary_max_tokens)
        for eid in cluster.participants
        if eid in domain_summaries
    ]

    per_expert_outputs: List[Dict[str, Any]] = []
    rounds_run = 0

    for round_idx in range(config.pipeline.max_discussion_rounds):
        round_outputs: List[Dict[str, Any]] = []
        for expert in participant_experts:
            others = [e for e in participant_experts if e.id != expert.id]
            base_system = _build_expert_system_prompt(expert, config)
            stage_system, stage_user = render_prompt(
                "stage2_context_discussion",
                context_topic=cluster.topic,
                my_expert=expert,
                other_participants=others,
                participant_summaries=relayed_summaries,
                language=config.language,
            )
            merged_system = base_system + "\n\n" + stage_system
            resp = await llm.query(
                # Stage 2 uses a single model (no in-domain cross-check here).
                model=config.models.default_review_models[0],
                system_prompt=merged_system,
                user_prompt=stage_user,
                temperature=config.models.temperature,
            )
            parsed = resp.parse_json() or {}
            if isinstance(parsed, dict):
                parsed.setdefault("context_topic", cluster.topic)
                parsed.setdefault("my_domain", expert.display_name(config.language))
            round_outputs.append(parsed)

        per_expert_outputs.extend(round_outputs)
        rounds_run += 1

        # Early stopping: if nobody added new content in this round, stop.
        if config.pipeline.enable_early_stopping and check_consensus(round_outputs):
            break

    return {
        "context_topic": cluster.topic,
        "participants": [e.id for e in participant_experts],
        "rounds_run": rounds_run,
        "expert_outputs": per_expert_outputs,
        "consensus_reached": check_consensus(per_expert_outputs[-len(participant_experts):]),
    }
