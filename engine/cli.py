"""Command-line entrypoint.

Usage:
    python -m engine.cli review --preset life-sciences --input project.json \\
        [--config custom_council.yaml] [--output report.json]
    python -m engine.cli list-presets
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from config.loader import PRESETS_DIR, load_council_config, load_preset

from .pipeline import run_ethics_review


def _cmd_review(args: argparse.Namespace) -> int:
    config = load_council_config(args.config)
    preset = load_preset(args.preset)
    project = json.loads(Path(args.input).read_text(encoding="utf-8"))

    result = asyncio.run(run_ethics_review(project, config, preset))

    if args.output:
        Path(args.output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote review to {args.output}", file=sys.stderr)
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


def _cmd_list_presets(_args: argparse.Namespace) -> int:
    for p in sorted(PRESETS_DIR.iterdir()):
        if p.is_dir() and (p / "preset.yaml").exists():
            try:
                preset = load_preset(p.name)
                print(f"{p.name:20s}  {preset.meta.name.zh or preset.meta.name.en or ''}")
            except Exception as e:                                        # noqa: BLE001
                print(f"{p.name:20s}  (error: {e})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser("ethics-council")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_review = sub.add_parser("review", help="Run a full ethics review")
    p_review.add_argument("--preset", required=True, help="Preset name, e.g. life-sciences")
    p_review.add_argument("--input", required=True, help="Path to project JSON")
    p_review.add_argument("--config", default=None, help="Optional override council.yaml")
    p_review.add_argument("--output", default=None, help="Write result here (stdout otherwise)")
    p_review.set_defaults(func=_cmd_review)

    p_list = sub.add_parser("list-presets", help="List available presets")
    p_list.set_defaults(func=_cmd_list_presets)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
