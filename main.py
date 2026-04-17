"""CLI entry point for the Ethics Council pipeline.

Usage:
    python main.py examples/example_project_genomics.json --preset life-sciences
    python main.py examples/example_project_ai.json --preset ai-ethics
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import ConfigLoader
from engine.pipeline import run_ethics_review
from engine.llm_client import make_llm_client


def main():
    parser = argparse.ArgumentParser(description="Run an Ethics Council review")
    parser.add_argument("project", help="Path to project JSON file")
    parser.add_argument("--preset", default="life-sciences", help="Preset name (default: life-sciences)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--provider", default=None, help="LLM provider override (stub, openrouter, anthropic, openai)")
    args = parser.parse_args()

    project_path = Path(args.project)
    if not project_path.exists():
        print(f"Error: project file not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    with open(project_path, encoding="utf-8") as f:
        project = json.load(f)

    loader = ConfigLoader(
        preset_name=args.preset,
        config_dir=str(PROJECT_ROOT / "config"),
        presets_dir=str(PROJECT_ROOT / "presets"),
    )
    config = loader.council
    preset = loader.preset

    if args.provider:
        llm = make_llm_client(args.provider, temperature=config.models.temperature)
    else:
        llm = None

    project_text = json.dumps(project, ensure_ascii=False, indent=2)
    result = asyncio.run(run_ethics_review(
        project_material=project_text,
        config=config,
        preset=preset,
        llm=llm,
    ))

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Review saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
