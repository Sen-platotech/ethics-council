"""Pydantic request/response models for Ethics Council API."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SubmitProjectRequest(BaseModel):
    """Request to submit a project for ethics review."""
    project_material: Dict[str, Any] = Field(..., description="Project submission material (matches project_input schema)")
    preset: str = Field(default="life-sciences", description="Preset package to use")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Optional config overrides")


class ConfirmExpertsRequest(BaseModel):
    """Request to confirm/modify expert selection after Stage 0."""
    review_id: str
    experts_selected: List[str] = Field(..., description="List of expert IDs to include")
    context_clusters: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional modified context clusters")
    expert_model_overrides: Optional[Dict[str, List[str]]] = Field(default=None, description="Per-expert model overrides")


class ReviewMetadata(BaseModel):
    """Review metadata for list view."""
    id: str
    created_at: str
    project_title: str
    preset: str
    status: str
    risk_level: Optional[str] = None


class ReviewDetail(BaseModel):
    """Full review with all stages."""
    id: str
    created_at: str
    project_material: Dict[str, Any]
    preset: str
    status: str
    routing_result: Optional[Dict[str, Any]] = None
    domain_results: Optional[Dict[str, Any]] = None
    context_discussions: Optional[List[Dict[str, Any]]] = None
    final_report: Optional[Dict[str, Any]] = None


class PresetInfo(BaseModel):
    """Information about an available preset."""
    id: str
    name: Dict[str, str]
    description: Dict[str, str]
    domain: str
    expert_count: int
    expert_ids: List[str]
