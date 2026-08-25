from app.analysis_pipeline import build_combined_result
from app.email_parser import parse_eml
from app.rule_engine import analyze_email_rules


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
    assert response.risk_level == "MEDIUM"
    assert isinstance(response.confidence, int)
    assert 0 <= response.confidence <= 100
    assert response.confidence_source == "deterministic_fallback"
