"""Deterministic numerical risk scoring."""

from app.schemas import Indicator, RiskAssessment


def calculate_risk(indicators: list[Indicator]) -> RiskAssessment:
    """Sum fixed rule contributions and cap the result at 100."""
    score = max(0, min(100, sum(indicator.score_contribution for indicator in indicators)))
    return RiskAssessment(risk_score=score, indicators=indicators)


def get_risk_level(score: int) -> str:
    """Map the final deterministic numerical score to its overall severity level."""
    bounded_score = max(0, min(100, score))
    if bounded_score <= 29:
        return "LOW"
    if bounded_score <= 59:
        return "MEDIUM"
    if bounded_score <= 79:
        return "HIGH"
    return "CRITICAL"
