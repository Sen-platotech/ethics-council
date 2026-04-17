# CLAUDE.md — Ethics Council

## What is this

A multi-agent ethics review system where multiple LLM "experts" collaboratively review research projects through a 4-stage async pipeline. Built on top of the karpathy/llm-council architecture, repurposed for structured ethics review with domain-specific expert presets.

## Quick start

```bash
# Install deps
pip install pyyaml jinja2 pydantic

# Run smoke tests (no API key needed — uses stub LLM)
python3 tests/test_smoke.py

# CLI review (stub mode)
python3 main.py examples/example_project_genomics.json --preset life-sciences

# Web app
cd frontend && npm install && cd ..
pip install fastapi uvicorn
./start.sh   # backend :8001, frontend :5173
```

## Architecture

### 4-stage pipeline (`engine/`)

- **Stage 0 — Router** (`router.py`): Selects relevant experts from the preset based on project flags and content. Outputs `RoutingResult` with `experts_selected` + `context_clusters`.
- **Stage 1 — Domain review** (`domain_review.py`): Each selected expert runs cross-validation with 2-3 LLMs (LLM-A first-pass → LLM-B cross-check → optional LLM-C → merge summary).
- **Stage 2 — Context discussion** (`context_discussion.py`): Experts in the same `context_cluster` discuss cross-domain risks in up to N rounds with early-stopping on consensus.
- **Stage 3 — Chairman** (`chairman.py`): Synthesizes all domain summaries + discussion outputs into a final ethics opinion with priority actions (P0/P1/P2).

### Config layer (`config/`)

- `schema.py`: Pydantic v2 models for `CouncilConfig`, `Expert`, `Preset`, `RoutingResult`, etc.
- `loader.py`: `ConfigLoader` loads `council_config.yaml` + a named preset. `render_prompt()` renders Jinja2 prompt templates from `prompts/`.
- `council_config.yaml`: Global settings (models, pipeline params, ethical framework principles).

### Presets (`presets/`)

Each preset is a directory: `preset.yaml` + `experts/*.yaml` + `cross_domain_templates.yaml`.

Available presets: `life-sciences` (8 experts), `ai-ethics` (6), `social-science` (6), `clinical-trial` (6).

### Prompts (`prompts/`)

Jinja2 YAML templates for each stage: `stage0_routing.yaml`, `stage1_review.yaml`, `stage1_cross_check.yaml`, `stage1_domain_summary.yaml`, `stage2_context_discussion.yaml`, `stage3_chairman.yaml`.

### Stub LLM client

`engine/llm_client.py` ships a `StubLLMClient` that returns shaped JSON for each stage by detecting keywords in the user prompt. Detection order matters: Stage 3 is checked first (since it embeds earlier-stage JSON containing their keywords).

Set `ETHICS_COUNCIL_LLM=stub` env var to force stub mode regardless of config.

### Backend (`backend/`)

FastAPI app: `POST /api/reviews` (submit + Stage 0), `POST /api/reviews/{id}/confirm` (Stages 1-3), `POST /api/reviews/{id}/confirm/stream` (SSE). JSON file storage in `data/reviews/`.

### Frontend (`frontend/`)

React + Vite. 4-step wizard: submit → expert selection → review progress (SSE) → final report.

## Key conventions

- `project_material` flows through the pipeline as a JSON string (not dict). Each engine function normalizes str/dict at entry.
- All Chinese-language prompts and expert definitions — this is for Chinese research ethics review.
- Expert `system_prompt` fields use Jinja2 with `{{ expert }}`, `{{ config }}`, `{{ ethical_framework }}` variables.
- The pipeline is fully async but stages run sequentially (0→1→2→3). Within Stage 1, experts could be parallelized but currently run sequentially for simplicity.

## Running tests

```bash
python3 tests/test_smoke.py
```

Tests 4 things: config loading for all presets, stub LLM keyword detection, life-sciences full pipeline, ai-ethics full pipeline.
