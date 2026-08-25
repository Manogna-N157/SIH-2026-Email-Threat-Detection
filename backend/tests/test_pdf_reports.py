import asyncio
import importlib
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app import case_storage
from app.analysis_pipeline import build_combined_result
from app.email_parser import parse_eml
from app.rule_engine import analyze_email_rules
from app.schemas import CaseCreateRequest
from app.report_generator import _confidence_label


api_module = importlib.import_module("app.main")


@pytest.fixture
def isolated_database(monkeypatch, tmp_path):
    monkeypatch.setattr(case_storage, "DATABASE_PATH", tmp_path / "cases.db")


def test_pdf_report_endpoint_returns_professional_pdf_with_case_evidence(isolated_database) -> None:
    parsed = parse_eml(
        b"""From: Finance <finance@example.com>
To: user@company.test
Subject: Invoice review
Authentication-Results: mx.test; spf=fail; dkim=pass; dmarc=fail
Received: from relay.example.com (relay.example.com [203.0.113.10]) by mx.test; Mon, 24 Aug 2026 09:00:00 +0000
Content-Type: text/plain; charset=utf-8

Review https://example.com/invoice."""
    )
    risk = analyze_email_rules(parsed)
    analysis = build_combined_result(parsed, risk, None, [])
    stored = CaseCreateRequest(
        case_id="pdf-case-001",
        timestamp=datetime(2026, 8, 24, 10, tzinfo=timezone.utc),
        filename="EMAIL-002.eml",
        risk_score=risk.risk_score,
        classification=analysis.classification,
        confidence=analysis.confidence,
        summary="Authentication failures require review.",
        indicators=risk.indicators,
        analysis=analysis,
    )
    asyncio.run(api_module.store_case(stored))

    response = asyncio.run(api_module.get_case_pdf_report("pdf-case-001"))

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF-")
    assert len(response.body) > 2_000
    assert 'filename="case-pdf-case-001-report.pdf"' in response.headers["content-disposition"]


def test_missing_case_pdf_report_returns_not_found(isolated_database) -> None:
    with pytest.raises(HTTPException) as error:
        asyncio.run(api_module.get_case_pdf_report("missing-case"))

    assert error.value.status_code == 404


def test_report_labels_unavailable_confidence_without_using_zero() -> None:
    assert _confidence_label(None) == "Not available"
    assert _confidence_label(77) == "77%"
