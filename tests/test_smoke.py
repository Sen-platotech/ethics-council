"""
End-to-end smoke test for the Ethics Council pipeline.

Runs the full 4-stage pipeline with the stub LLM client against
the example genomics project using the life-sciences preset.
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import ConfigLoader
from engine.pipeline import run_ethics_review
from engine.llm_client import StubLLMClient


def test_full_pipeline_life_sciences():
    """Smoke test: life-sciences preset with genomics example project."""
    # Load config + preset
    loader = ConfigLoader(
        preset_name="life-sciences",
        config_dir=str(PROJECT_ROOT / "config"),
        presets_dir=str(PROJECT_ROOT / "presets"),
    )
    config = loader.council
    preset = loader.preset

    assert preset.meta.id == "life-sciences"
    assert len(preset.experts) == 8
    assert len(preset.cross_domain_templates) > 0

    # Load example project
    with open(PROJECT_ROOT / "examples" / "example_project_genomics.json") as f:
        project = json.load(f)

    project_text = json.dumps(project, ensure_ascii=False, indent=2)
    llm = StubLLMClient()

    # Run the full pipeline
    result = asyncio.run(run_ethics_review(
        project_material=project_text,
        config=config,
        preset=preset,
        llm=llm,
    ))

    # Verify result structure
    assert result is not None
    print(f"  Result keys: {list(result.keys())}")
    # The _routing key should be present
    assert "_routing" in result
    # The stub chairman generates these keys
    assert "project_name" in result or "overall_conclusion" in result or "chairman_notes" in result or "note" in result

    print("PASS: life-sciences full pipeline smoke test")
    routing = result["_routing"]
    print(f"  Risk level: {routing.get('risk_level', 'N/A')}")
    print(f"  Experts selected: {[e['id'] for e in routing.get('experts_selected', [])]}")
    if "_deliberation_log" in result:
        dlog = result["_deliberation_log"]
        dr = dlog.get("domain_results", [])
        if isinstance(dr, list):
            print(f"  Domain results: {len(dr)} experts")
        else:
            print(f"  Domain results: {list(dr.keys())}")
        print(f"  Context discussions: {len(dlog.get('context_discussions', []))}")


def test_full_pipeline_ai_ethics():
    """Smoke test: ai-ethics preset with AI example project."""
    loader = ConfigLoader(
        preset_name="ai-ethics",
        config_dir=str(PROJECT_ROOT / "config"),
        presets_dir=str(PROJECT_ROOT / "presets"),
    )
    config = loader.council
    preset = loader.preset

    assert preset.meta.id == "ai-ethics"
    assert len(preset.experts) == 6

    with open(PROJECT_ROOT / "examples" / "example_project_ai.json") as f:
        project = json.load(f)

    project_text = json.dumps(project, ensure_ascii=False, indent=2)
    llm = StubLLMClient()

    result = asyncio.run(run_ethics_review(
        project_material=project_text,
        config=config,
        preset=preset,
        llm=llm,
    ))

    assert result is not None
    assert "_routing" in result

    print("PASS: ai-ethics full pipeline smoke test")
    print(f"  Result keys: {list(result.keys())}")


def test_config_loading():
    """Verify all presets load without errors."""
    presets_dir = PROJECT_ROOT / "presets"
    for p in sorted(presets_dir.iterdir()):
        if not p.is_dir():
            continue
        loader = ConfigLoader(
            preset_name=p.name,
            config_dir=str(PROJECT_ROOT / "config"),
            presets_dir=str(presets_dir),
        )
        assert loader.council is not None
        assert loader.preset is not None
        assert len(loader.preset.experts) > 0
        print(f"PASS: loaded preset '{p.name}' ({len(loader.preset.experts)} experts)")


def test_stub_llm_deterministic():
    """Verify StubLLMClient returns shaped responses for all stage keywords."""
    llm = StubLLMClient()

    # Stage 0: routing (needs both keywords)
    resp = asyncio.run(llm.query("test-model", "system", "experts_selected context_clusters [human_subjects] [data_privacy]"))
    data = resp.parse_json()
    assert "experts_selected" in data

    # Stage 1: first-pass review (needs all three keywords)
    resp = asyncio.run(llm.query("test-model", "你是一位资深的测试专家，", "risk_items missing_information key_concerns_summary"))
    data = resp.parse_json()
    assert "risk_items" in data

    # Stage 1: cross-check (needs both keywords)
    resp = asyncio.run(llm.query("test-model", "system", "missed_risks severity_adjustments"))
    data = resp.parse_json()
    assert "missed_risks" in data

    # Stage 2: discussion (needs both keywords)
    resp = asyncio.run(llm.query("test-model", "system", 'cross_domain_risks supplements_to_others collaborative_recommendations "context_topic": "测试议题"'))
    data = resp.parse_json()
    assert "cross_domain_risks" in data

    # Stage 3: chairman (needs both keywords)
    resp = asyncio.run(llm.query("test-model", "system", "priority_actions chairman_notes domain_assessments"))
    data = resp.parse_json()
    assert "priority_actions" in data

    print("PASS: StubLLMClient deterministic responses")


if __name__ == "__main__":
    print("=" * 60)
    print("Ethics Council — End-to-End Smoke Tests")
    print("=" * 60)
    print()

    test_config_loading()
    print()
    test_stub_llm_deterministic()
    print()
    test_full_pipeline_life_sciences()
    print()
    test_full_pipeline_ai_ethics()
    print()
    print("=" * 60)
    print("All smoke tests passed!")
    print("=" * 60)
