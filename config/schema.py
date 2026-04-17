"""Pydantic schemas for validating council.yaml, expert definitions, and presets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


# --------------------------- council.yaml --------------------------- #

class EthicalPrinciple(BaseModel):
    name: str
    description: str
    source: Optional[str] = None


class EthicalFramework(BaseModel):
    principles: List[EthicalPrinciple] = Field(default_factory=list)
    universal_review_criteria: List[str] = Field(default_factory=list)
    high_risk_checklist: List[str] = Field(default_factory=list)


class ModelsConfig(BaseModel):
    router_model: str
    chairman_model: str
    default_review_models: List[str]
    max_models_per_domain: int = 3
    min_models_per_domain: int = 2
    api_provider: str = "stub"
    temperature: float = 0.3
    request_timeout: float = 120.0


class DiversityCheck(BaseModel):
    enabled: bool = True
    min_experts: int = 3
    require_ethics_expert: bool = False
    require_legal_expert: bool = True


class PipelineConfig(BaseModel):
    enable_stage0_routing: bool = True
    enable_cross_domain_discussion: bool = True
    enable_early_stopping: bool = True
    max_discussion_rounds: int = 2
    summary_relay: bool = True
    summary_max_tokens: int = 500
    diversity_check: DiversityCheck = Field(default_factory=DiversityCheck)


class OutputConfig(BaseModel):
    format: str = "json"           # json / markdown
    include_deliberation_log: bool = True
    include_divergences: bool = True
    language: str = "zh-CN"


class CouncilMeta(BaseModel):
    name: str
    language: str = "zh-CN"
    version: str = "1.0"


class CouncilConfig(BaseModel):
    """Top-level council.yaml schema."""
    model_config = ConfigDict(extra="allow")

    council: CouncilMeta
    ethical_framework: EthicalFramework
    models: ModelsConfig
    pipeline: PipelineConfig
    output: OutputConfig

    @property
    def language(self) -> str:
        return self.council.language


# --------------------------- Expert definition --------------------------- #

class LocalizedName(BaseModel):
    model_config = ConfigDict(extra="allow")
    zh: Optional[str] = None
    en: Optional[str] = None


class RegulatoryEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    scope: Optional[str] = None
    key_provisions: Optional[str] = None


class TriggerConditions(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    project_flags: List[str] = Field(default_factory=list)


class CrossDomainRelation(BaseModel):
    partner: str
    topics: List[str] = Field(default_factory=list)


class Expert(BaseModel):
    """A reviewer persona definition."""
    model_config = ConfigDict(extra="allow")

    id: str
    name: LocalizedName
    review_dimensions: List[str] = Field(default_factory=list)
    regulatory_knowledge: List[RegulatoryEntry] = Field(default_factory=list)
    trigger_conditions: TriggerConditions = Field(default_factory=TriggerConditions)
    cross_domain_relations: List[CrossDomainRelation] = Field(default_factory=list)
    system_prompt: str = ""
    tags: List[str] = Field(default_factory=list)   # e.g. ["ethics", "legal"]

    def display_name(self, language: str = "zh-CN") -> str:
        lang_key = language.split("-")[0]
        return getattr(self.name, lang_key, None) or self.name.zh or self.name.en or self.id


# --------------------------- Preset --------------------------- #

class CrossDomainTemplate(BaseModel):
    topic: str
    participants: List[str]
    typical_triggers: List[str] = Field(default_factory=list)


class PresetMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: LocalizedName
    description: Optional[Union[str, Dict[str, str]]] = None
    domain: Optional[str] = None
    version: str = "1.0"


class Preset(BaseModel):
    meta: PresetMeta
    experts: List[Expert]
    cross_domain_templates: List[CrossDomainTemplate] = Field(default_factory=list)
    ethical_framework_override: Optional[EthicalFramework] = None

    def expert_by_id(self, expert_id: str) -> Optional[Expert]:
        return next((e for e in self.experts if e.id == expert_id), None)


# --------------------------- Runtime context --------------------------- #

class ContextCluster(BaseModel):
    """A Stage 2 discussion group (topic + participant expert IDs)."""
    topic: str
    participants: List[str]
    reason: Optional[str] = None


class RoutingResult(BaseModel):
    experts_selected: List[Dict[str, Any]]
    context_clusters: List[ContextCluster]
    experts_not_needed: List[Dict[str, Any]] = Field(default_factory=list)
    high_risk_flags: List[str] = Field(default_factory=list)
    risk_level: str = "standard"   # standard / elevated / high
