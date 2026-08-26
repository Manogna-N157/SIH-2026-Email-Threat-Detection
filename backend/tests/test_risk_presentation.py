import pytest
from app.analysis_pipeline import build_combined_result
from app.email_parser import parse_eml
from app.risk_engine import get_risk_level
from app.rule_engine import analyze_email_rules
from app.schemas import CompleteAnalyzeResponse, AIAnalysis, EmailDetails, TechnicalAuthentication, ThreatGraph


def test_phishing_classification_and_medium_risk_level_are_independent() -> None:
    parsed = parse_eml(
        b"""From: sender@example.com
To: recipient@example.com
Subject: Urgent account verification
Content-Type: text/plain; charset=utf-8

Verify your password immediately at http://example.test/login."""
    )

    assessment = analyze_email_rules(parsed)
    response = build_combined_result(parsed, assessment, None, [])

    assert assessment.risk_score == 35
    assert response.classification == "PHISHING"
    assert response.risk_level == "LOW"
    assert isinstance(response.confidence, int)
    assert 0 <= response.confidence <= 100
    assert response.confidence_source == "deterministic_fallback"


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (0, "LOW"),
        (35, "LOW"),
        (49, "LOW"),
        (50, "MEDIUM"),
        (74, "MEDIUM"),
        (75, "HIGH"),
        (100, "HIGH"),
    ],
)
def test_risk_level_threshold_boundaries(score: int, expected_level: str) -> None:
    assert get_risk_level(score) == expected_level


def test_score_35_can_never_have_medium_or_high_risk_level() -> None:
    assert get_risk_level(35) == "LOW"
    # Even if instantiated with a mismatched risk_level, model_validator enforces LOW for score 35
    response = CompleteAnalyzeResponse(
        case_id="test-35",
        risk_score=35,
        risk_level="MEDIUM",  # intentionally passing wrong level to test enforcement
        classification="PHISHING",
        confidence=80,
        confidence_source="deterministic_fallback",
        email=EmailDetails(headers={}, plain_text_body=""),
        authentication=TechnicalAuthentication(authentication_results=[]),
        indicators=[],
        ai_analysis=AIAnalysis(available=False, result=None),
        urls=[],
        domains=[],
        ips=[],
        ip_intelligence=[],
        timeline=[],
        threat_graph=ThreatGraph(nodes=[], edges=[]),
    )
    assert response.risk_level == "LOW"
