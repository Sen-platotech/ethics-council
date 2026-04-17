"""FastAPI backend for Ethics Council."""

import sys
import json
import uuid
import asyncio
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add project root to path so engine/config modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from . import storage
from .config import PROJECT_ROOT, DEFAULT_PRESET
from .models import (
    SubmitProjectRequest,
    ConfirmExpertsRequest,
    ReviewMetadata,
    ReviewDetail,
    PresetInfo,
)
from config.loader import ConfigLoader
from config.schema import RoutingResult, ContextCluster
from engine.pipeline import run_ethics_review
from engine.llm_client import make_llm_client

app = FastAPI(title="Ethics Council API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config_and_preset(preset_name: str, config_overrides: dict | None = None):
    """Load council config and a named preset."""
    loader = ConfigLoader(
        preset_name=preset_name,
        config_dir=str(PROJECT_ROOT / "config"),
        presets_dir=str(PROJECT_ROOT / "presets"),
    )
    return loader.council, loader.preset


def _available_presets() -> List[PresetInfo]:
    """Scan the presets/ directory and return info for each preset."""
    presets_dir = PROJECT_ROOT / "presets"
    results = []
    for p in sorted(presets_dir.iterdir()):
        if not p.is_dir():
            continue
        try:
            loader = ConfigLoader(
                preset_name=p.name,
                config_dir=str(PROJECT_ROOT / "config"),
                presets_dir=str(presets_dir),
            )
            preset = loader.preset
            results.append(PresetInfo(
                id=preset.meta.id,
                name={"zh": preset.meta.name.zh, "en": preset.meta.name.en},
                description={"zh": getattr(preset.meta, "description", {}).get("zh", ""), "en": getattr(preset.meta, "description", {}).get("en", "")} if hasattr(preset.meta, "description") else {"zh": "", "en": ""},
                domain=preset.meta.domain,
                expert_count=len(preset.experts),
                expert_ids=[e.id for e in preset.experts],
            ))
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "service": "Ethics Council API"}


@app.get("/api/presets", response_model=List[PresetInfo])
async def list_presets():
    """List all available preset packages."""
    return _available_presets()


@app.get("/api/reviews", response_model=List[ReviewMetadata])
async def list_reviews():
    """List all reviews (metadata only)."""
    return storage.list_reviews()


@app.post("/api/reviews")
async def create_review(request: SubmitProjectRequest):
    """
    Submit a project for ethics review.
    Runs Stage 0 (routing) and returns the routing result for user confirmation.
    """
    review_id = str(uuid.uuid4())

    # Persist the review record
    review = storage.create_review(review_id, request.project_material, request.preset)

    # Load config + preset
    config, preset = _load_config_and_preset(request.preset)

    # Prepare project material as text
    project_text = json.dumps(request.project_material, ensure_ascii=False, indent=2)

    # Run Stage 0 routing
    llm = make_llm_client(config.models.api_provider)

    from engine.router import select_experts
    routing_result = await select_experts(
        project_text, preset.experts, preset.cross_domain_templates, config, llm
    )

    # Save routing result
    routing_dict = routing_result.model_dump()
    storage.update_review(review_id, status="routing_complete", routing_result=routing_dict)

    return {
        "review_id": review_id,
        "routing_result": routing_dict,
        "available_experts": [
            {
                "id": e.id,
                "name": {"zh": e.name.zh, "en": e.name.en},
                "tags": e.tags,
                "review_dimensions": e.review_dimensions,
            }
            for e in preset.experts
        ],
    }


@app.get("/api/reviews/{review_id}", response_model=ReviewDetail)
async def get_review(review_id: str):
    """Get a specific review with all its data."""
    review = storage.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/api/reviews/{review_id}/confirm")
async def confirm_and_run(review_id: str, request: ConfirmExpertsRequest):
    """
    Confirm expert selection and run Stages 1-3.
    Returns the complete review result.
    """
    review = storage.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    if review["status"] not in ("routing_complete", "submitted"):
        raise HTTPException(status_code=400, detail=f"Review is in status '{review['status']}', expected 'routing_complete'")

    # Save confirmed experts
    storage.update_review(
        review_id,
        status="running",
        confirmed_experts=request.experts_selected,
        confirmed_clusters=request.context_clusters,
        expert_model_overrides=request.expert_model_overrides,
    )

    config, preset = _load_config_and_preset(review["preset"])
    project_text = json.dumps(review["project_material"], ensure_ascii=False, indent=2)
    llm = make_llm_client(config.models.api_provider)

    # Build a user_confirm callback that applies the already-confirmed choices
    def user_confirm(routing: RoutingResult) -> RoutingResult:
        # Filter experts to only those confirmed
        routing.experts_selected = [
            e for e in routing.experts_selected if e["id"] in request.experts_selected
        ]
        # Override clusters if provided
        if request.context_clusters is not None:
            routing.context_clusters = [
                ContextCluster(**c) for c in request.context_clusters
            ]
        return routing

    # Run the full pipeline
    result = await run_ethics_review(
        project_material=project_text,
        config=config,
        preset=preset,
        llm=llm,
        user_confirm=user_confirm,
        expert_model_overrides=request.expert_model_overrides,
    )

    # Separate pipeline internals from the final report
    routing_info = result.pop("_routing", None)
    deliberation_log = result.pop("_deliberation_log", None)

    # Persist results
    storage.update_review(
        review_id,
        status="completed",
        final_report=result,
        domain_results=deliberation_log.get("domain_results") if deliberation_log else None,
        context_discussions=deliberation_log.get("context_discussions") if deliberation_log else None,
    )

    return {
        "review_id": review_id,
        "status": "completed",
        "final_report": result,
        "domain_results": deliberation_log.get("domain_results") if deliberation_log else None,
        "context_discussions": deliberation_log.get("context_discussions") if deliberation_log else None,
    }


@app.post("/api/reviews/{review_id}/confirm/stream")
async def confirm_and_run_stream(review_id: str, request: ConfirmExpertsRequest):
    """
    Confirm expert selection and stream Stages 1-3 progress via SSE.
    """
    review = storage.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    if review["status"] not in ("routing_complete", "submitted"):
        raise HTTPException(status_code=400, detail=f"Review is in status '{review['status']}', expected 'routing_complete'")

    storage.update_review(
        review_id,
        status="running",
        confirmed_experts=request.experts_selected,
        confirmed_clusters=request.context_clusters,
        expert_model_overrides=request.expert_model_overrides,
    )

    async def event_generator():
        try:
            config, preset = _load_config_and_preset(review["preset"])
            project_text = json.dumps(review["project_material"], ensure_ascii=False, indent=2)
            llm = make_llm_client(config.models.api_provider)

            # ---- Stage 1: Domain reviews ----
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"

            from engine.domain_review import run_cross_validation

            selected_experts = [e for e in preset.experts if e.id in request.experts_selected]
            models = config.models.default_review_models

            domain_results = {}
            for expert in selected_experts:
                yield f"data: {json.dumps({'type': 'stage1_expert_start', 'expert_id': expert.id, 'expert_name': expert.display_name()})}\n\n"
                expert_models = models
                if request.expert_model_overrides and expert.id in request.expert_model_overrides:
                    expert_models = request.expert_model_overrides[expert.id]
                result = await run_cross_validation(project_text, expert, expert_models, config, llm)
                domain_results[expert.id] = result
                yield f"data: {json.dumps({'type': 'stage1_expert_complete', 'expert_id': expert.id, 'data': result})}\n\n"

            yield f"data: {json.dumps({'type': 'stage1_complete'})}\n\n"

            # ---- Stage 2: Cross-domain discussion ----
            context_discussions = []
            routing_result = review.get("routing_result", {})
            clusters_raw = request.context_clusters or routing_result.get("context_clusters", [])
            clusters = [ContextCluster(**c) if isinstance(c, dict) else c for c in clusters_raw]

            if config.pipeline.enable_cross_domain_discussion and clusters:
                yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"

                from engine.context_discussion import run_discussion

                for cluster in clusters:
                    participants = [e for e in selected_experts if e.id in cluster.participants]
                    if len(participants) < 2:
                        continue
                    summaries = {eid: domain_results[eid] for eid in cluster.participants if eid in domain_results}
                    yield f"data: {json.dumps({'type': 'stage2_cluster_start', 'topic': cluster.topic})}\n\n"
                    disc = await run_discussion(cluster, participants, summaries, config, llm)
                    context_discussions.append(disc)
                    yield f"data: {json.dumps({'type': 'stage2_cluster_complete', 'topic': cluster.topic, 'data': disc})}\n\n"

                yield f"data: {json.dumps({'type': 'stage2_complete'})}\n\n"

            # ---- Stage 3: Chairman synthesis ----
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"

            from engine.chairman import synthesize

            risk_level = routing_result.get("risk_level", "standard")
            final_report = await synthesize(
                project_text,
                list(domain_results.values()),
                context_discussions,
                risk_level,
                config,
                llm,
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': final_report})}\n\n"

            # Persist
            storage.update_review(
                review_id,
                status="completed",
                final_report=final_report,
                domain_results=domain_results,
                context_discussions=context_discussions,
            )

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.delete("/api/reviews/{review_id}")
async def delete_review(review_id: str):
    """Delete a review."""
    if not storage.delete_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found")
    return {"status": "deleted"}


if __name__ == "__main__":
    import uvicorn
    from .config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT)
