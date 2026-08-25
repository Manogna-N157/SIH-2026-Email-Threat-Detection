from types import SimpleNamespace

import pytest

from app.ai import gemini_analyzer
from app.email_parser import parse_eml
from app.rule_engine import analyze_email_rules
from app.schemas import GeminiAnalysis


@pytest.fixture
def parsed_email_and_risk():
    parsed = parse_eml(
        b"""From: sender@example.com
Reply-To: reply@example.net
Subject: Verify your account
Content-Type: text/plain; charset=utf-8

Please verify your password at http://example.test/login immediately."""
    )
    return parsed, analyze_email_rules(parsed)


class FakeClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.prompt = None
        self.models = self

    def generate_content(self, **kwargs):
        self.prompt = kwargs["contents"]
        if self.error:
            raise self.error
        return self.response


def test_returns_valid_structured_gemini_analysis(monkeypatch, parsed_email_and_risk) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    parsed, risk = parsed_email_and_risk
    client = FakeClient(
        SimpleNamespace(
            parsed=GeminiAnalysis(
                classification="PHISHING",
                confidence=91,
                threat_categories=["credential-harvesting"],
                explanation="The message requests credentials through an insecure link.",
                recommended_action="QUARANTINE",
            )
        )
    )

    result = gemini_analyzer.analyze_with_gemini(parsed, risk, client=client)

    assert result is not None
    assert result.classification == "PHISHING"
    assert "deterministic_security_indicators" in client.prompt
    assert "Do not calculate or return any numerical risk score" in client.prompt


def test_missing_api_key_skips_gemini(monkeypatch, parsed_email_and_risk) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_analyzer, "ENV_FILE", "missing.env")
    parsed, risk = parsed_email_and_risk

    assert gemini_analyzer.analyze_with_gemini(parsed, risk) is None


@pytest.mark.parametrize(
    "response",
    [SimpleNamespace(parsed=None, text="not json"), SimpleNamespace(parsed={"classification": "UNKNOWN"})],
)
def test_invalid_gemini_response_falls_back_to_deterministic(monkeypatch, parsed_email_and_risk, response) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    parsed, risk = parsed_email_and_risk

    assert gemini_analyzer.analyze_with_gemini(parsed, risk, client=FakeClient(response)) is None


@pytest.mark.parametrize("error", [TimeoutError(), RuntimeError("rate limited"), RuntimeError("service unavailable")])
def test_gemini_failures_do_not_raise(monkeypatch, parsed_email_and_risk, error) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    parsed, risk = parsed_email_and_risk

    assert gemini_analyzer.analyze_with_gemini(parsed, risk, client=FakeClient(error=error)) is None
