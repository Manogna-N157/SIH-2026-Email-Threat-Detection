"""Evidence-based confidence estimation when semantic AI is unavailable."""

from __future__ import annotations

from app.schemas import Indicator


CLASSIFICATION_BASE_CONFIDENCE = {
    "LEGITIMATE": 80,
    "SUSPICIOUS": 55,
    "PHISHING": 60,
    "IMPERSONATION": 62,
    "BUSINESS_EMAIL_COMPROMISE": 65,
    "MALWARE": 68,
}


def calculate_deterministic_confidence(
    risk_score: int,
    classification: str,
    indicators: list[Indicator],
) -> int:
    """Estimate confidence from deterministic evidence, never unavailable AI.

    The base reflects the specificity of the deterministic classification. It is
    strengthened by independent matched indicators and the bounded evidence
    score. This is a repeatable evidence-consistency measure, not an AI value.
    """
    score = max(0, min(100, risk_score))
    base = CLASSIFICATION_BASE_CONFIDENCE.get(classification, 50)
    evidence_support = min(20, (len(indicators) * 4) + (score // 10))
    return max(0, min(100, base + evidence_support))
