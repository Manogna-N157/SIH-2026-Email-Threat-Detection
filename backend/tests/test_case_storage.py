import asyncio
import importlib
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app import case_storage
from app.analysis_pipeline import build_combined_result
from app.email_parser import parse_eml
from app.schemas import CaseCreateRequest, GeminiAnalysis, Indicator
from app.rule_engine import analyze_email_rules


api_module = importlib.import_module("app.main")


@pytest.fixture
def isolated_database(monkeypatch, tmp_path):
    monkeypatch.setattr(case_storage, "DATABASE_PATH", tmp_path / "cases.db")
    case_storage.clear_remembered_analyses()


def _case(case_id: str, timestamp: datetime) -> CaseCreateRequest:
    return CaseCreateRequest(
        case_id=case_id,
        timestamp=timestamp,
        filename="EMAIL-002.eml",
        risk_score=85,
        classification="PHISHING",
        confidence=90,
        summary="Credential-harvesting indicators were detected.",
        indicators=[
            Indicator(
                name="SPF failure",
                severity="high",
                explanation="SPF returned fail.",
                score_contribution=15,
            )
        ],
    )


def test_case_endpoints_create_list_and_get(isolated_database) -> None:
    older = _case("case-older", datetime(2026, 8, 24, 9, tzinfo=timezone.utc))
    newer = _case("case-newer", datetime(2026, 8, 24, 10, tzinfo=timezone.utc))

    saved_older = asyncio.run(api_module.store_case(older))
    saved_newer = asyncio.run(api_module.store_case(newer))
    listed = asyncio.run(api_module.list_stored_cases())
    retrieved = asyncio.run(api_module.get_stored_case("case-older"))

    assert saved_older.case_id == "case-older"
    assert saved_newer.indicators[0].name == "SPF failure"
    assert [case.case_id for case in listed] == ["case-newer", "case-older"]
    assert retrieved.summary == "Credential-harvesting indicators were detected."
    assert retrieved.indicators[0].score_contribution == 15


def test_duplicate_and_missing_cases_return_http_errors(isolated_database) -> None:
    case = _case("case-duplicate", datetime(2026, 8, 24, 9, tzinfo=timezone.utc))
    asyncio.run(api_module.store_case(case))

    with pytest.raises(HTTPException) as duplicate_error:
        asyncio.run(api_module.store_case(case))
    with pytest.raises(HTTPException) as missing_error:
        asyncio.run(api_module.get_stored_case("does-not-exist"))

    assert duplicate_error.value.status_code == 409
    assert missing_error.value.status_code == 404


def test_legacy_snapshot_without_risk_level_remains_readable(isolated_database) -> None:
    case = _case("legacy-case", datetime(2026, 8, 24, 9, tzinfo=timezone.utc))
    legacy_analysis = {
        "case_id": "legacy-case",
        "risk_score": 35,
        "risk_level": "MEDIUM",
        "classification": "PHISHING",
        "confidence": 0,
        "email": {"headers": {}},
        "authentication": {},
        "indicators": [],
        "ai_analysis": {"available": False, "result": None},
        "urls": [], "domains": [], "ips": [], "ip_intelligence": [], "timeline": [],
        "threat_graph": {"nodes": [], "edges": []},
    }
    case_storage._initialize_database()
    with sqlite3.connect(case_storage.DATABASE_PATH) as connection:
        connection.execute(
            "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case.case_id, case.timestamp.isoformat(), case.filename, case.risk_score,
                case.classification, 0, case.summary,
                json.dumps([indicator.model_dump() for indicator in case.indicators]), json.dumps(legacy_analysis),
            ),
        )

    stored = asyncio.run(api_module.list_stored_cases())[0]

    assert stored.analysis is not None
    assert stored.analysis.risk_level == "LOW"
    assert stored.analysis.confidence == 63
    assert stored.analysis.confidence_source == "deterministic_fallback"
    assert stored.confidence == 63


def test_malformed_stale_row_does_not_break_case_list(isolated_database) -> None:
    valid = _case("valid-case", datetime(2026, 8, 24, 10, tzinfo=timezone.utc))
    asyncio.run(api_module.store_case(valid))
    case_storage._initialize_database()
    with sqlite3.connect(case_storage.DATABASE_PATH) as connection:
        connection.execute(
            "INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("broken-case", "not-a-date", "broken.eml", 20, "SUSPICIOUS", None, "bad", "not-json", "{"),
        )

    cases = asyncio.run(api_module.list_stored_cases())

    assert [case.case_id for case in cases] == ["valid-case"]


def test_case_creation_persists_matching_ai_analysis_from_completed_upload(isolated_database) -> None:
    parsed = parse_eml(
        b"From: sender@example.com\nContent-Type: text/plain\n\nVerify your password at http://example.test/login."
    )
    risk = analyze_email_rules(parsed)
    ai_result = GeminiAnalysis(
        classification="PHISHING",
        confidence=88,
        threat_categories=["credential-harvesting"],
        explanation="The message requests a password through an insecure link.",
        recommended_action="QUARANTINE",
    )
    analysis = build_combined_result(parsed, risk, ai_result, [])
    case_storage.remember_analysis(analysis)
    case = CaseCreateRequest(
        case_id=analysis.case_id,
        timestamp=datetime(2026, 8, 26, 9, tzinfo=timezone.utc),
        filename="ai-analysis.eml",
        risk_score=0,
        classification="LEGITIMATE",
        confidence=None,
        summary="Stored from completed upload.",
    )

    stored = asyncio.run(api_module.store_case(case))
    retrieved = asyncio.run(api_module.get_stored_case(analysis.case_id))

    assert stored.risk_score == analysis.risk_score
    assert stored.analysis is not None
    assert retrieved.analysis is not None
    assert retrieved.analysis.ai_analysis.available is True
    assert retrieved.analysis.ai_analysis.result == ai_result


def test_case_creation_persists_ai_analysis_when_provided_in_request(isolated_database) -> None:
    parsed = parse_eml(
        b"From: sender@example.com\nContent-Type: text/plain\n\nVerify your password at http://example.test/login."
    )
    risk = analyze_email_rules(parsed)
    ai_result = GeminiAnalysis(
        classification="PHISHING",
        confidence=88,
        threat_categories=["credential-harvesting"],
        explanation="The message requests a password through an insecure link.",
        recommended_action="QUARANTINE",
    )
    analysis = build_combined_result(parsed, risk, ai_result, [])
    case = CaseCreateRequest(
        case_id="custom-client-case-id-123",
        timestamp=datetime(2026, 8, 26, 9, tzinfo=timezone.utc),
        filename="ai-analysis-direct.eml",
        risk_score=analysis.risk_score,
        classification=analysis.classification,
        confidence=analysis.confidence,
        summary="Stored directly with analysis payload.",
        analysis=analysis,
    )

    stored = asyncio.run(api_module.store_case(case))
    retrieved = asyncio.run(api_module.get_stored_case("custom-client-case-id-123"))

    assert stored.analysis is not None
    assert retrieved.analysis is not None
    assert retrieved.analysis.case_id == "custom-client-case-id-123"
    assert retrieved.analysis.ai_analysis.available is True
    assert retrieved.analysis.ai_analysis.result == ai_result


def test_stored_case_always_has_risk_level_derived_from_risk_score(isolated_database) -> None:
    """Risk level on StoredCase must always match the backend authoritative thresholds."""
    low = _case("low-risk", datetime(2026, 8, 26, 9, tzinfo=timezone.utc))
    low.risk_score = 35
    saved_low = asyncio.run(api_module.store_case(low))
    retrieved_low = asyncio.run(api_module.get_stored_case("low-risk"))

    assert saved_low.risk_level == "LOW"
    assert retrieved_low.risk_level == "LOW"

    high = _case("high-risk", datetime(2026, 8, 26, 10, tzinfo=timezone.utc))
    high.risk_score = 85
    saved_high = asyncio.run(api_module.store_case(high))
    retrieved_high = asyncio.run(api_module.get_stored_case("high-risk"))

    assert saved_high.risk_level == "HIGH"
    assert retrieved_high.risk_level == "HIGH"


def test_risk_level_threshold_boundaries_on_stored_cases(isolated_database) -> None:
    """Every boundary score must produce the correct risk_level on StoredCase."""
    for idx, (score, expected) in enumerate([(0, "LOW"), (35, "LOW"), (49, "LOW"), (50, "MEDIUM"), (74, "MEDIUM"), (75, "HIGH"), (100, "HIGH")]):
        cid = f"boundary-{score}"
        case = _case(cid, datetime(2026, 8, 26, 9, tzinfo=timezone.utc))
        case.risk_score = score
        asyncio.run(api_module.store_case(case))
        retrieved = asyncio.run(api_module.get_stored_case(cid))
        assert retrieved.risk_level == expected, f"Score {score} should be {expected}, got {retrieved.risk_level}"


def test_ai_semantic_analysis_roundtrips_through_full_lifecycle(isolated_database) -> None:
    """Regression: the complete upload → save → retrieve cycle preserves AI semantic analysis."""
    parsed = parse_eml(
        b"From: ceo@bigcorp.com\nTo: cfo@bigcorp.com\nSubject: Wire transfer\n"
        b"Content-Type: text/plain\n\nUrgent: wire $50k to this account."
    )
    risk = analyze_email_rules(parsed)
    ai_result = GeminiAnalysis(
        classification="BUSINESS_EMAIL_COMPROMISE",
        confidence=92,
        threat_categories=["wire-fraud", "executive-impersonation"],
        explanation="The email impersonates a CEO requesting an urgent wire transfer.",
        recommended_action="BLOCK",
    )
    analysis = build_combined_result(parsed, risk, ai_result, [])
    # Simulate what the frontend does: remember, then store with custom case_id
    custom_id = "regression-test-lifecycle-001"
    case = CaseCreateRequest(
        case_id=custom_id,
        timestamp=datetime(2026, 8, 26, 12, tzinfo=timezone.utc),
        filename="bec-test.eml",
        risk_score=analysis.risk_score,
        classification=analysis.classification,
        confidence=analysis.confidence,
        summary="Regression test for AI semantic analysis lifecycle.",
        analysis=analysis,
    )

    stored = asyncio.run(api_module.store_case(case))
    retrieved = asyncio.run(api_module.get_stored_case(custom_id))

    # Verify the analysis is fully persisted and retrievable
    assert stored.analysis is not None
    assert stored.analysis.ai_analysis.available is True
    assert stored.analysis.ai_analysis.result is not None
    assert stored.analysis.ai_analysis.result.classification == "BUSINESS_EMAIL_COMPROMISE"
    assert stored.analysis.ai_analysis.result.confidence == 92
    assert stored.analysis.ai_analysis.result.explanation == "The email impersonates a CEO requesting an urgent wire transfer."
    assert stored.analysis.ai_analysis.result.recommended_action == "BLOCK"
    assert stored.analysis.ai_analysis.result.threat_categories == ["wire-fraud", "executive-impersonation"]
    assert stored.analysis.confidence_source == "ai_semantic"

    # Verify roundtrip through the database
    assert retrieved.analysis is not None
    assert retrieved.analysis.ai_analysis.available is True
    assert retrieved.analysis.ai_analysis.result == ai_result
    from app.risk_engine import get_risk_level
    assert retrieved.risk_level == get_risk_level(analysis.risk_score)
    assert retrieved.classification == "BUSINESS_EMAIL_COMPROMISE"

