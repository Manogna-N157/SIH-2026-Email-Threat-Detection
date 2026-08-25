import asyncio
import importlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.schemas import GeminiAnalysis


api_module = importlib.import_module("app.main")
DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.mark.parametrize(
    "filename", ["EMAIL-001.eml", "EMAIL-002.eml", "EMAIL-003.eml", "EMAIL-008.eml", "EMAIL-012.eml"]
)
def test_complete_pipeline_returns_deterministic_and_mocked_gemini_results(monkeypatch, filename: str) -> None:
    mocked_ai = GeminiAnalysis(
        classification="SUSPICIOUS",
        confidence=77,
        threat_categories=["test-category"],
        explanation="Mocked Gemini analysis for pipeline verification.",
        recommended_action="MONITOR",
    )
    monkeypatch.setattr(api_module, "analyze_with_gemini", lambda _email, _risk: mocked_ai)
    monkeypatch.setattr(api_module, "resolve_domain_intelligence", lambda _domains: [])
    upload = UploadFile(filename=filename, file=BytesIO((DATASET_DIR / filename).read_bytes()))

    response = asyncio.run(api_module.analyze_email(upload))

    assert response.case_id
    assert 0 <= response.risk_score <= 100
    assert response.classification == "SUSPICIOUS"
    assert response.confidence == 77
    assert response.confidence_source == "ai_semantic"
    assert response.email.subject is not None
    assert isinstance(response.authentication.spf, list)
    assert isinstance(response.indicators, list)
    assert response.ai_analysis.available is True
    assert response.ai_analysis.result == mocked_ai
    assert isinstance(response.urls, list)
    assert isinstance(response.domains, list)
    assert isinstance(response.ips, list)
    assert isinstance(response.ip_intelligence, list)
    assert isinstance(response.timeline, list)
    assert isinstance(response.threat_graph.nodes, list)
    assert isinstance(response.threat_graph.edges, list)


def test_pipeline_keeps_deterministic_result_when_gemini_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "analyze_with_gemini", lambda _email, _risk: None)
    monkeypatch.setattr(api_module, "resolve_domain_intelligence", lambda _domains: [])
    upload = UploadFile(
        filename="EMAIL-002.eml", file=BytesIO((DATASET_DIR / "EMAIL-002.eml").read_bytes())
    )

    response = asyncio.run(api_module.analyze_email(upload))

    assert response.risk_score == 100
    assert response.classification == "PHISHING"
    assert isinstance(response.confidence, int)
    assert 0 <= response.confidence <= 100
    assert response.confidence_source == "deterministic_fallback"
    assert response.risk_level == "CRITICAL"
    assert response.ai_analysis.available is False
    assert response.ai_analysis.result is None


def test_legitimate_email_has_deterministic_confidence_without_gemini(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "analyze_with_gemini", lambda _email, _risk: None)
    monkeypatch.setattr(api_module, "resolve_domain_intelligence", lambda _domains: [])
    upload = UploadFile(
        filename="EMAIL-001.eml", file=BytesIO((DATASET_DIR / "EMAIL-001.eml").read_bytes())
    )

    response = asyncio.run(api_module.analyze_email(upload))

    assert response.classification == "LEGITIMATE"
    assert isinstance(response.confidence, int)
    assert 0 <= response.confidence <= 100
    assert response.confidence_source == "deterministic_fallback"
    assert response.ai_analysis.available is False


def test_dns_resolution_failure_does_not_break_analysis(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "analyze_with_gemini", lambda _email, _risk: None)
    monkeypatch.setattr(api_module, "resolve_domain_intelligence", lambda _domains: (_ for _ in ()).throw(OSError()))
    upload = UploadFile(
        filename="dns-failure.eml",
        file=BytesIO(b"From: sender@example.com\nContent-Type: text/plain\n\nVisit https://example.test/login"),
    )

    response = asyncio.run(api_module.analyze_email(upload))

    assert response.ip_intelligence == []
    assert response.risk_score == 15
