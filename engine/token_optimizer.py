"""Token-optimization utilities: summary relay, early stopping."""

from __future__ import annotations

from typing import Any, Dict, List


def count_by_severity(risk_items: List[Dict[str, Any]], severity: str) -> int:
    return sum(1 for r in risk_items if (r.get("severity") or "").lower() == severity.lower())


def extract_summary_for_relay(stage1_output: Dict[str, Any], max_tokens: int = 500) -> Dict[str, Any]:
    """Distill a Stage 1 output into the minimal payload for downstream stages.

    max_tokens is advisory; we simply truncate the free-text summary.
    """
    risks = stage1_output.get("risk_items", []) or []
    summary_text = stage1_output.get("key_concerns_summary", "") or ""
    # Coarse char-based cap (≈1 char ≈ 1.5 tokens for CJK; we stay conservative).
    cap_chars = max_tokens * 2
    if len(summary_text) > cap_chars:
        summary_text = summary_text[: cap_chars - 1] + "…"
    return {
        "expert_domain": stage1_output.get("expert_domain"),
        "overall_assessment": stage1_output.get("overall_assessment"),
        "confidence": stage1_output.get("confidence"),
        "key_concerns_summary": summary_text,
        "risk_count": {
            "high": count_by_severity(risks, "high"),
            "medium": count_by_severity(risks, "medium"),
            "low": count_by_severity(risks, "low"),
        },
        "top_risks": risks[:3],
    }


def check_consensus(discussion_results: List[Dict[str, Any]]) -> bool:
    """True if nobody added a new cross-domain risk or supplement → stop early."""
    if not discussion_results:
        return True
    new_risks = sum(len(r.get("cross_domain_risks") or []) for r in discussion_results)
    supplements = sum(len(r.get("supplements_to_others") or []) for r in discussion_results)
    return new_risks == 0 and supplements == 0
