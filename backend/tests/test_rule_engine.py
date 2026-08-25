from pathlib import Path

import pytest

from app.email_parser import parse_eml
from app.rule_engine import analyze_email_rules
from app.risk_engine import get_risk_level


DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
WORKSPACE_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("filename", "expected_indicators", "minimum_score"),
    [
        ("EMAIL-001.eml", set(), 0),
        ("EMAIL-002.eml", {"SPF failure", "DKIM failure", "DMARC failure", "Credential request"}, 80),
        ("EMAIL-003.eml", {"Reply-To mismatch", "Payment request", "BEC indicator", "Display-name impersonation"}, 60),
        ("EMAIL-008.eml", {"Suspicious attachment"}, 18),
        ("EMAIL-012.eml", {"SPF failure", "DMARC failure", "Credential request", "Urgency/social engineering"}, 60),
    ],
)
def test_synthetic_dataset_rules_are_deterministic(
    filename: str, expected_indicators: set[str], minimum_score: int
) -> None:
    parsed = parse_eml((DATASET_DIR / filename).read_bytes())

    first = analyze_email_rules(parsed)
    second = analyze_email_rules(parsed)
    names = {indicator.name for indicator in first.indicators}

    assert first == second
    assert 0 <= first.risk_score <= 100
    assert expected_indicators.issubset(names)
    assert first.risk_score >= minimum_score


def test_legitimate_synthetic_email_has_no_indicators() -> None:
    parsed = parse_eml((DATASET_DIR / "EMAIL-001.eml").read_bytes())
    assessment = analyze_email_rules(parsed)

    assert assessment.risk_score == 0
    assert assessment.indicators == []


def test_high_risk_uploaded_email_uses_recovered_content_for_scoring() -> None:
    parsed = parse_eml((WORKSPACE_DIR / "high_risk_test.eml").read_bytes())
    assessment = analyze_email_rules(parsed)
    names = {indicator.name for indicator in assessment.indicators}

    assert {
        "Suspicious URL",
        "Suspicious domain pattern",
        "Credential-harvesting link",
        "Credential request",
        "Urgency/social engineering",
    }.issubset(names)
    assert assessment.risk_score >= 60
    assert get_risk_level(assessment.risk_score) == "HIGH"


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [(0, "LOW"), (29, "LOW"), (30, "MEDIUM"), (59, "MEDIUM"), (60, "HIGH"), (79, "HIGH"), (80, "CRITICAL"), (100, "CRITICAL")],
)
def test_risk_level_uses_only_final_numerical_score(score: int, expected_level: str) -> None:
    assert get_risk_level(score) == expected_level
