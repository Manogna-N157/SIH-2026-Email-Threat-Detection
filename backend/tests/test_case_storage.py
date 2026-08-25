import asyncio
import importlib
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app import case_storage
from app.schemas import CaseCreateRequest, Indicator


api_module = importlib.import_module("app.main")


@pytest.fixture
def isolated_database(monkeypatch, tmp_path):
    monkeypatch.setattr(case_storage, "DATABASE_PATH", tmp_path / "cases.db")


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
    assert stored.analysis.risk_level == "MEDIUM"
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
