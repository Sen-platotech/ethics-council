"""JSON-based storage for ethics reviews."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_review_path(review_id: str) -> str:
    """Get the file path for a review."""
    return os.path.join(DATA_DIR, f"{review_id}.json")


def create_review(review_id: str, project_material: Dict[str, Any], preset: str) -> Dict[str, Any]:
    """Create a new review record."""
    ensure_data_dir()

    review = {
        "id": review_id,
        "created_at": datetime.utcnow().isoformat(),
        "project_material": project_material,
        "preset": preset,
        "status": "submitted",
        "routing_result": None,
        "confirmed_experts": None,
        "confirmed_clusters": None,
        "expert_model_overrides": None,
        "domain_results": None,
        "context_discussions": None,
        "final_report": None,
    }

    path = get_review_path(review_id)
    with open(path, "w") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

    return review


def get_review(review_id: str) -> Optional[Dict[str, Any]]:
    """Load a review from storage."""
    path = get_review_path(review_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_review(review: Dict[str, Any]):
    """Save a review to storage."""
    ensure_data_dir()
    path = get_review_path(review["id"])
    with open(path, "w") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)


def update_review(review_id: str, **fields) -> Dict[str, Any]:
    """Update specific fields of a review."""
    review = get_review(review_id)
    if review is None:
        raise ValueError(f"Review {review_id} not found")
    review.update(fields)
    save_review(review)
    return review


def list_reviews() -> List[Dict[str, Any]]:
    """List all reviews (metadata only)."""
    ensure_data_dir()

    reviews = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            path = os.path.join(DATA_DIR, filename)
            with open(path, "r") as f:
                data = json.load(f)
                reviews.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "project_title": data.get("project_material", {}).get("project_title", "Untitled"),
                    "preset": data.get("preset", "unknown"),
                    "status": data.get("status", "unknown"),
                    "risk_level": (data.get("routing_result") or {}).get("risk_level"),
                })

    reviews.sort(key=lambda x: x["created_at"], reverse=True)
    return reviews


def delete_review(review_id: str) -> bool:
    """Delete a review."""
    path = get_review_path(review_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
