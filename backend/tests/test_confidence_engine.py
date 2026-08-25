from app.confidence_engine import calculate_deterministic_confidence
from app.schemas import Indicator


def test_deterministic_confidence_is_repeatable_and_bounded() -> None:
    indicators = [
        Indicator(
            name="Credential request",
            severity="high",
            explanation="The message asks for credentials.",
            score_contribution=15,
        ),
        Indicator(
            name="Suspicious URL",
            severity="medium",
            explanation="The message contains a suspicious URL.",
            score_contribution=12,
        ),
    ]

    first = calculate_deterministic_confidence(35, "PHISHING", indicators)
    second = calculate_deterministic_confidence(35, "PHISHING", indicators)

    assert first == second
    assert 0 <= first <= 100


def test_deterministic_confidence_clamps_invalid_score_input() -> None:
    assert calculate_deterministic_confidence(500, "MALWARE", []) == 78
    assert calculate_deterministic_confidence(-1, "LEGITIMATE", []) == 80
