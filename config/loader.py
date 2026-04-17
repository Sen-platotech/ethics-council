"""YAML / preset loader + Jinja2 prompt renderer."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jinja2
import yaml

from .schema import (
    CouncilConfig,
    CrossDomainTemplate,
    EthicalFramework,
    Expert,
    Preset,
    PresetMeta,
)


# ---------- Paths ----------

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
DEFAULT_COUNCIL_YAML = _THIS_DIR / "defaults.yaml"
PRESETS_DIR = _REPO_ROOT / "presets"
PROMPTS_DIR = _REPO_ROOT / "prompts"


# ---------- Basic YAML helpers ----------

def _load_yaml(path: os.PathLike | str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursive dict merge — override wins, but nested dicts are merged."""
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# ---------- Public API ----------

def load_council_config(user_config_path: Optional[os.PathLike | str] = None) -> CouncilConfig:
    """Load defaults.yaml, optionally merging a user-provided council.yaml on top."""
    data = _load_yaml(DEFAULT_COUNCIL_YAML)
    if user_config_path:
        user = _load_yaml(user_config_path)
        data = _deep_merge(data, user)
    return CouncilConfig(**data)


def load_preset(preset_name: str, presets_dir: Optional[os.PathLike | str] = None) -> Preset:
    """Load a named preset package from presets/<name>/."""
    base = Path(presets_dir) if presets_dir else PRESETS_DIR
    preset_dir = base / preset_name
    if not preset_dir.exists():
        raise FileNotFoundError(f"Preset not found: {preset_dir}")

    meta_path = preset_dir / "preset.yaml"
    meta_raw = _load_yaml(meta_path)
    # Meta file may embed either {preset: {...}} or the fields directly.
    meta_section = meta_raw.get("preset", meta_raw)
    meta = PresetMeta(**meta_section)

    # Experts
    experts: list[Expert] = []
    expert_files = sorted(glob.glob(str(preset_dir / "experts" / "*.yaml")))
    for f in expert_files:
        raw = _load_yaml(f)
        # Support both {expert: {...}} and flat form.
        section = raw.get("expert", raw)
        experts.append(Expert(**section))

    # Cross-domain templates
    templates: list[CrossDomainTemplate] = []
    cdt_path = preset_dir / "cross_domain_templates.yaml"
    if cdt_path.exists():
        raw = _load_yaml(cdt_path)
        lst = raw.get("cross_domain_templates", raw if isinstance(raw, list) else [])
        for item in lst:
            templates.append(CrossDomainTemplate(**item))

    # Optional per-preset ethical framework override
    override: Optional[EthicalFramework] = None
    fw_path = preset_dir / "ethical_framework.yaml"
    if fw_path.exists():
        raw = _load_yaml(fw_path)
        section = raw.get("ethical_framework", raw)
        override = EthicalFramework(**section)

    return Preset(
        meta=meta,
        experts=experts,
        cross_domain_templates=templates,
        ethical_framework_override=override,
    )


# ---------- Jinja2 prompt rendering ----------

_JINJA_ENV = jinja2.Environment(
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    undefined=jinja2.StrictUndefined,
)


def _tojson_filter(value: Any, indent: Optional[int] = None) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, indent=indent, default=str)


_JINJA_ENV.filters["tojson"] = _tojson_filter


def render_prompt(template_name: str, **context: Any) -> Tuple[str, str]:
    """Render a prompt YAML that has `system:` and `user:` fields.

    Returns: (system_prompt, user_prompt). Either may be empty string if
    the template omits it.
    """
    path = PROMPTS_DIR / f"{template_name}.yaml"
    raw = _load_yaml(path)
    # Use Jinja env (not StrictUndefined for templates — allow optional vars).
    env = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["tojson"] = _tojson_filter

    system = env.from_string(raw.get("system") or "").render(**context)
    user = env.from_string(raw.get("user") or "").render(**context)
    return system, user


def render_string(template: str, **context: Any) -> str:
    """Render an ad-hoc Jinja string (used for expert.system_prompt fields)."""
    env = jinja2.Environment(autoescape=False)
    env.filters["tojson"] = _tojson_filter
    return env.from_string(template).render(**context)


# ---------- Convenience facade ----------

class ConfigLoader:
    """Small facade that holds council + preset together."""

    def __init__(
        self,
        council_config_path: Optional[os.PathLike | str] = None,
        preset_name: Optional[str] = None,
        config_dir: Optional[os.PathLike | str] = None,
        presets_dir: Optional[os.PathLike | str] = None,
    ):
        # If config_dir is given, use defaults.yaml from that directory
        if config_dir and not council_config_path:
            candidate = Path(config_dir) / "defaults.yaml"
            # We pass None to use the built-in default, but load_council_config
            # already uses DEFAULT_COUNCIL_YAML when user_config_path is None.
            # Only override if a custom config_dir is supplied.
            self.council = load_council_config()
        else:
            self.council = load_council_config(council_config_path)

        self._presets_dir = presets_dir
        self.preset = load_preset(preset_name, presets_dir) if preset_name else None

    def reload_preset(self, preset_name: str) -> Preset:
        self.preset = load_preset(preset_name, self._presets_dir)
        return self.preset

    def list_experts(self) -> list[Expert]:
        return list(self.preset.experts) if self.preset else []
