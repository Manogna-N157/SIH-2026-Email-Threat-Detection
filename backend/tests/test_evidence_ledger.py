import asyncio
import importlib
from datetime import datetime, timezone

import pytest

from app import case_storage
from app.evidence_ledger import GENESIS_HASH, evidence_hash
from app.schemas import CaseCreateRequest, Indicator, StoredCase


api_module = importlib.import_module("app.main")


@pytest.fixture
def isolated_database(monkeypatch, tmp_path):
    monkeypatch.setattr(case_storage, "DATABASE_PATH", tmp_path / "cases.db")


def _case(case_id: str, hour: int) -> CaseCreateRequest:
    return CaseCreateRequest(
        case_id=case_id,
        timestamp=datetime(2026, 8, 26, hour, tzinfo=timezone.utc),
        filename="evidence-test.eml",
        risk_score=65,
        classification="PHISHING",
        confidence=84,
        summary="Deterministic phishing indicators found.",
        indicators=[
            Indicator(
                name="Credential request",
                severity="high",
                explanation="The message asks for a password.",
                score_contribution=15,
            )
        ],
    )


def test_evidence_hash_is_deterministic() -> None:
    stored_case = StoredCase(**_case("hash-case", 9).model_dump())

    assert evidence_hash(stored_case) == evidence_hash(stored_case)
    assert len(evidence_hash(stored_case)) == 64


def test_first_and_subsequent_blocks_are_chained(isolated_database) -> None:
    case_storage.create_case(_case("case-one", 9))
    case_storage.create_case(_case("case-two", 10))

    first, second = case_storage.list_evidence_blocks()

    assert first.index == 0
    assert first.previous_hash == GENESIS_HASH
    assert second.index == 1
    assert second.previous_hash == first.current_hash


def test_unchanged_case_evidence_verifies(isolated_database) -> None:
    case_storage.create_case(_case("verified-case", 9))

    response = asyncio.run(api_module.verify_case_blockchain_evidence("verified-case"))

    assert response.verified is True
    assert response.block is not None
    assert response.message == "Evidence integrity verified. No tampering detected."


def test_modified_case_evidence_fails_verification(isolated_database) -> None:
    case_storage.create_case(_case("modified-case", 9))
    with case_storage._connect() as connection:
        connection.execute("UPDATE cases SET risk_score = ? WHERE case_id = ?", (20, "modified-case"))

    response = asyncio.run(api_module.verify_case_blockchain_evidence("modified-case"))

    assert response.verified is False
    assert response.message == "Evidence integrity check failed. Possible tampering detected."
