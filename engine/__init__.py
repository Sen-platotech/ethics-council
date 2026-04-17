"""Ethics Council engine layer — generic orchestration for Stage 0-3 pipeline.

The engine knows nothing about ethics. "What to review, by what standards,
who reviews" is entirely defined by config files in presets/ and prompts/.
"""

from .pipeline import run_ethics_review  # noqa: F401
